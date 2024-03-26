#  Copyright 2024 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from unittest import mock

import pytest
import yaml
from rest_framework import status
from rest_framework.test import APIClient

from aap_eda.api.constants import (
    PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
)
from aap_eda.core import models
from aap_eda.core.enums import Action, ProcessParentType, ResourceType
from aap_eda.core.models.event_stream import (
    RestartCompletionInterval,
    RestartFailureInterval,
    RestartFailureLimit,
    RetentionFailurePeriod,
    RetentionSuccessPeriod,
)
from tests.integration.constants import api_url_v1

BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_TYPE = """
---
- name: PG Notify Template Event Stream
  hosts: all
  sources:
    - name: my_range
      ansible.eda.range:
        limit: 5
      complementary_source:
        name: Postgres Listener
        args:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channels:
            - "{{ EDA_PG_NOTIFY_CHANNEL }}"
      extra_vars:
        EDA_PG_NOTIFY_DSN: "{{ settings.PG_NOTIFY_DSN }}"
        EDA_PG_NOTIFY_CHANNEL: "{{ event_stream.channel_name }}"
      encrypt_vars:
        - EDA_PG_NOTIFY_DSN
  rules:
    - name: Post event
      condition: true
      action:
        pg_notify:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channel: "{{ EDA_PG_NOTIFY_CHANNEL }}"
          event: "{{ event }}"
"""
BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_NAME = """
---
- name: PG Notify Template Event Stream
  hosts: all
  sources:
    - name: my_range
      ansible.eda.range:
        limit: 5
      complementary_source:
        type: ansible.eda.pg_listener
        args:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channels:
            - "{{ EDA_PG_NOTIFY_CHANNEL }}"
      extra_vars:
        EDA_PG_NOTIFY_DSN: "{{ settings.PG_NOTIFY_DSN }}"
        EDA_PG_NOTIFY_CHANNEL: "{{ event_stream.channel_name }}"
      encrypt_vars:
        - EDA_PG_NOTIFY_DSN
  rules:
    - name: Post event
      condition: true
      action:
        pg_notify:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channel: "{{ EDA_PG_NOTIFY_CHANNEL }}"
          event: "{{ event }}"
"""
BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_ARGS = """
---
- name: PG Notify Template Event Stream
  hosts: all
  sources:
    - name: my_range
      ansible.eda.range:
        limit: 5
      complementary_source:
        type: ansible.eda.pg_listener
        name: Postgres Listener
      extra_vars:
        EDA_PG_NOTIFY_DSN: "{{ settings.PG_NOTIFY_DSN }}"
        EDA_PG_NOTIFY_CHANNEL: "{{ event_stream.channel_name }}"
      encrypt_vars:
        - EDA_PG_NOTIFY_DSN
  rules:
    - name: Post event
      condition: true
      action:
        pg_notify:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channel: "{{ EDA_PG_NOTIFY_CHANNEL }}"
          event: "{{ event }}"
"""
BAD_PG_NOTIFY_NO_COMPLEMENTARY_SOURCE = """
---
- name: PG Notify Template Event Stream
  hosts: all
  sources:
    - name: my_range
      ansible.eda.range:
        limit: 5
      extra_vars:
        EDA_PG_NOTIFY_DSN: "{{ settings.PG_NOTIFY_DSN }}"
        EDA_PG_NOTIFY_CHANNEL: "{{ event_stream.channel_name }}"
      encrypt_vars:
        - EDA_PG_NOTIFY_DSN
  rules:
    - name: Post event
      condition: true
      action:
        pg_notify:
          dsn: "{{ EDA_PG_NOTIFY_DSN }}"
          channel: "{{ EDA_PG_NOTIFY_CHANNEL }}"
          event: "{{ event }}"
"""


@pytest.mark.django_db
def test_list_event_streams(
    client: APIClient,
    check_permission_mock: mock.Mock,
    default_de: models.DecisionEnvironment,
    default_user: models.User,
):
    event_streams = models.EventStream.objects.bulk_create(
        [
            models.EventStream(
                name="test-event_stream-1",
                source_type="ansible.eda.range",
                source_args={"limit": 5, "delay": 1},
                user=default_user,
                decision_environment_id=default_de.id,
            ),
            models.EventStream(
                name="test-event_stream-2",
                source_type="ansible.eda.range",
                source_args={"limit": 6, "delay": 2},
                user=default_user,
                decision_environment_id=default_de.id,
            ),
        ]
    )

    response = client.get(f"{api_url_v1}/event-streams/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 2
    assert (
        response.data["results"][1]["source_type"]
        == event_streams[0].source_type
    )
    assert response.data["results"][1]["name"] == event_streams[0].name
    assert response.data["results"][1]["user"] == "luke.skywalker"

    check_permission_mock.assert_called_once_with(
        mock.ANY, mock.ANY, ResourceType.EVENT_STREAM, Action.READ
    )


@pytest.mark.django_db
def test_retrieve_event_stream(
    client: APIClient,
    check_permission_mock: mock.Mock,
    default_de: models.DecisionEnvironment,
    default_user: models.User,
):
    args = {"limit": 5, "delay": 1}
    event_stream = models.EventStream.objects.create(
        name="test-event_stream-1",
        source_type="ansible.eda.range",
        source_args=args,
        user=default_user,
        decision_environment_id=default_de.id,
    )

    response = client.get(f"{api_url_v1}/event-streams/{event_stream.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == event_stream.name
    assert response.data["source_type"] == event_stream.source_type
    assert yaml.safe_load(response.data["source_args"]) == args
    assert response.data["user"] == "luke.skywalker"

    check_permission_mock.assert_called_once_with(
        mock.ANY, mock.ANY, ResourceType.EVENT_STREAM, Action.READ
    )


@pytest.mark.django_db
def test_create_event_stream(
    client: APIClient,
    default_de: models.DecisionEnvironment,
    settings,
):
    models.Rulebook.objects.create(
        name=PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
        rulesets=PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    )

    args = {"limit": 5, "delay": 1}
    source_type = "ansible.eda.range"
    data_in = {
        "name": "test_event_stream",
        "source_type": f"{source_type}",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_201_CREATED
    result = response.data
    assert result["name"] == "test_event_stream"
    assert result["source_type"] == source_type
    assert result["user"] == "test.admin"
    assert yaml.safe_load(response.data["source_args"]) == args

    event_stream = models.EventStream.objects.first()
    rulesets = yaml.safe_load(event_stream.rulebook_rulesets)
    source = rulesets[0]["sources"][0]
    assert source[source_type] == args
    assert source["name"] == "test_event_stream"

    assert (
        event_stream.restart_completion_interval
        == RestartCompletionInterval.DEFAULT
    )
    if RestartCompletionInterval.DEFAULT == RestartCompletionInterval.SETTINGS:
        assert (
            event_stream.effective_restart_completion_interval
            == settings.ACTIVATION_RESTART_SECONDS_ON_COMPLETE
        )

    assert (
        event_stream.restart_failure_interval == RestartFailureInterval.DEFAULT
    )
    if RestartFailureInterval.DEFAULT == RestartFailureInterval.SETTINGS:
        assert (
            event_stream.effective_restart_failure_interval
            == settings.ACTIVATION_RESTART_SECONDS_ON_FAILURE
        )

    assert event_stream.restart_failure_limit == RestartFailureLimit.DEFAULT
    if RestartFailureLimit.DEFAULT == RestartFailureLimit.SETTINGS:
        assert (
            event_stream.effective_restart_failure_limit
            == settings.ACTIVATION_MAX_RESTARTS_ON_FAILURE
        )

    assert (
        event_stream.retention_failure_period == RetentionFailurePeriod.DEFAULT
    )
    if RetentionFailurePeriod.DEFAULT == RetentionFailurePeriod.SETTINGS:
        assert (
            event_stream.effective_retention_failure_period
            == settings.ACTIVATION_RETENTION_FAILURE_HOURS * 3600
        ) or (
            (
                settings.ACTIVATION_RETENTION_FAILURE_HOURS
                == RetentionFailurePeriod.FOREVER
            )
            and (
                event_stream.effective_retention_failure_period
                == settings.ACTIVATION_RETENTION_FAILURE_HOURS
            )
        )

    assert (
        event_stream.retention_success_period == RetentionSuccessPeriod.DEFAULT
    )
    if RetentionSuccessPeriod.DEFAULT == RetentionSuccessPeriod.SETTINGS:
        assert (
            event_stream.effective_retention_success_period
            == settings.ACTIVATION_RETENTION_SUCCESS_HOURS * 3600
        ) or (
            (
                settings.ACTIVATION_RETENTION_SUCCESS_HOURS
                == RetentionSuccessPeriod.FOREVER
            )
            and (
                event_stream.effective_retention_success_period
                == settings.ACTIVATION_RETENTION_SUCCESS_HOURS
            )
        )


@pytest.mark.parametrize(
    "param_data",
    [
        {
            "param": "restart_completion_interval",
            "value": RestartCompletionInterval.MINIMUM - 1,
            "expect": {
                "status": status.HTTP_400_BAD_REQUEST,
                "message": (
                    "Ensure this value is greater than or equal to"
                    f" {RestartCompletionInterval.MINIMUM}."
                ),
            },
        },
        {
            "param": "restart_completion_interval",
            "value": RestartCompletionInterval.MINIMUM,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_completion_interval",
            "value": RestartCompletionInterval.SETTINGS,
            "expect": {
                "status": status.HTTP_201_CREATED,
                "effective": {
                    "property": "effective_restart_completion_interval",
                    "setting": "ACTIVATION_RESTART_SECONDS_ON_COMPLETE",
                },
            },
        },
        {
            "param": "restart_completion_interval",
            "value": RestartCompletionInterval.DEFAULT,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_completion_interval",
            "value": RestartCompletionInterval.DEFAULT + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_interval",
            "value": RestartFailureInterval.MINIMUM - 1,
            "expect": {
                "status": status.HTTP_400_BAD_REQUEST,
                "message": (
                    "Ensure this value is greater than or equal to"
                    f" {RestartFailureInterval.MINIMUM}."
                ),
            },
        },
        {
            "param": "restart_failure_interval",
            "value": RestartFailureInterval.MINIMUM,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_interval",
            "value": RestartFailureInterval.SETTINGS,
            "expect": {
                "status": status.HTTP_201_CREATED,
                "effective": {
                    "property": "effective_restart_failure_interval",
                    "setting": "ACTIVATION_RESTART_SECONDS_ON_FAILURE",
                },
            },
        },
        {
            "param": "restart_failure_interval",
            "value": RestartFailureInterval.DEFAULT,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_interval",
            "value": RestartFailureInterval.DEFAULT + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.MINIMUM - 1,
            "expect": {
                "status": status.HTTP_400_BAD_REQUEST,
                "message": (
                    "Ensure this value is greater than or equal to"
                    f" {RestartFailureLimit.MINIMUM}."
                ),
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.MINIMUM,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.SETTINGS,
            "expect": {
                "status": status.HTTP_201_CREATED,
                "effective": {
                    "property": "effective_restart_failure_limit",
                    "setting": "ACTIVATION_MAX_RESTARTS_ON_FAILURE",
                },
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.DEFAULT,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.DEFAULT + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "restart_failure_limit",
            "value": RestartFailureLimit.UNLIMITED + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
    ],
)
@pytest.mark.django_db
def test_create_event_stream_with_restart_params(
    client: APIClient,
    default_de: models.DecisionEnvironment,
    param_data: dict,
    settings,
):
    models.Rulebook.objects.create(
        name=PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
        rulesets=PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    )

    param = param_data["param"]
    value = param_data["value"]

    args = {"limit": 5, "delay": 1}
    source_type = "ansible.eda.range"
    data_in = {
        "name": "test_event_stream",
        "source_type": f"{source_type}",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    } | {param: value}
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == param_data["expect"]["status"]
    if response.status_code == status.HTTP_201_CREATED:
        event_stream = models.EventStream.objects.first()
        assert getattr(event_stream, param) == value
        effective = param_data["expect"].get("effective", None)
        if effective:
            assert getattr(event_stream, effective["property"]) == getattr(
                settings, effective["setting"]
            )
    else:
        assert response.data[param][0] == param_data["expect"]["message"]


@pytest.mark.parametrize(
    "param_data",
    [
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.MINIMUM - 1,
            "expect": {
                "status": status.HTTP_400_BAD_REQUEST,
                "message": (
                    "Ensure this value is greater than or equal to"
                    f" {RetentionFailurePeriod.MINIMUM}."
                ),
            },
        },
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.MINIMUM,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.SETTINGS,
            "expect": {
                "status": status.HTTP_201_CREATED,
                "effective": {
                    "property": "effective_retention_failure_period",
                    "setting": "ACTIVATION_RETENTION_FAILURE_HOURS",
                },
            },
        },
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.DEFAULT,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.DEFAULT + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_failure_period",
            "value": RetentionFailurePeriod.FOREVER + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.MINIMUM - 1,
            "expect": {
                "status": status.HTTP_400_BAD_REQUEST,
                "message": (
                    "Ensure this value is greater than or equal to"
                    f" {RetentionSuccessPeriod.MINIMUM}."
                ),
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.MINIMUM,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.SETTINGS,
            "expect": {
                "status": status.HTTP_201_CREATED,
                "effective": {
                    "property": "effective_retention_success_period",
                    "setting": "ACTIVATION_RETENTION_SUCCESS_HOURS",
                },
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.DEFAULT,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.DEFAULT + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
        {
            "param": "retention_success_period",
            "value": RetentionSuccessPeriod.FOREVER + 1,
            "expect": {
                "status": status.HTTP_201_CREATED,
            },
        },
    ],
)
@pytest.mark.django_db
def test_create_event_stream_with_retention_params(
    client: APIClient,
    default_de: models.DecisionEnvironment,
    param_data: dict,
    settings,
):
    models.Rulebook.objects.create(
        name=PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
        rulesets=PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    )

    param = param_data["param"]
    value = param_data["value"]

    args = {"limit": 5, "delay": 1}
    source_type = "ansible.eda.range"
    data_in = {
        "name": "test_event_stream",
        "source_type": f"{source_type}",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    } | {param: value}
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == param_data["expect"]["status"]
    if response.status_code == status.HTTP_201_CREATED:
        event_stream = models.EventStream.objects.first()
        assert getattr(event_stream, param) == value
        effective = param_data["expect"].get("effective", None)
        if effective:
            assert getattr(event_stream, effective["property"]) == (
                getattr(settings, effective["setting"]) * 3600
            )  # conver to seconds
    else:
        assert response.data[param][0] == param_data["expect"]["message"]


@pytest.mark.django_db
def test_create_event_stream_with_different_default_channel_names(
    client: APIClient,
    default_de: models.DecisionEnvironment,
):
    models.Rulebook.objects.create(
        name=PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
        rulesets=PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    )

    args = {"limit": 5, "delay": 1}
    source_type = "ansible.eda.range"
    data_in_1 = {
        "name": "test_event_stream",
        "source_type": f"{source_type}",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in_1)
    assert response.status_code == status.HTTP_201_CREATED

    data_in_2 = {
        "name": "test_event_stream_2",
        "source_type": f"{source_type}",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in_2)

    assert response.status_code == status.HTTP_201_CREATED
    assert models.EventStream.objects.count() == 2
    assert (
        models.EventStream.objects.first().channel_name
        != models.EventStream.objects.last().channel_name
    )


@pytest.mark.django_db
def test_create_event_stream_with_credential(
    client: APIClient,
    default_de: models.DecisionEnvironment,
):
    models.Rulebook.objects.create(
        name=PG_NOTIFY_TEMPLATE_RULEBOOK_NAME,
        rulesets=PG_NOTIFY_TEMPLATE_RULEBOOK_DATA,
    )

    args = {"limit": 5, "delay": 1}
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.range",
        "source_args": f"{args}",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_201_CREATED
    result = response.data
    assert result["name"] == "test_event_stream"
    assert result["source_type"] == "ansible.eda.range"
    assert yaml.safe_load(response.data["source_args"]) == args


@pytest.mark.parametrize(
    "bad_rulebooks",
    [
        {"bad_rulebook_1": f"{BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_TYPE}"},
        {"bad_rulebook_2": f"{BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_NAME}"},
        {"bad_rulebook_3": f"{BAD_PG_NOTIFY_TEMPLATE_RULEBOOK_NO_ARGS}"},
        {"bad_rulebook_4": f"{BAD_PG_NOTIFY_NO_COMPLEMENTARY_SOURCE}"},
    ],
)
@pytest.mark.django_db
def test_create_event_stream_with_bad_rulebook(
    client: APIClient,
    default_de: models.DecisionEnvironment,
    settings,
    bad_rulebooks,
):
    for key in bad_rulebooks:
        settings.PG_NOTIFY_TEMPLATE_RULEBOOK = key
        settings.PG_NOTIFY_DSN = (
            "host=localhost port=5432 dbname=eda user=postgres password=secret"
        )
        models.Rulebook.objects.create(
            name=key,
            rulesets=bad_rulebooks[key],
        )

        args = {"limit": 5, "delay": 1}
        data_in = {
            "name": "test_event_stream",
            "source_type": "ansible.eda.range",
            "source_args": f"{args}",
            "decision_environment_id": default_de.id,
        }
        response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["detail"].startswith(
            "Configuration Error: Event stream template rulebook is missing "
        )


@pytest.mark.django_db
def test_create_event_stream_bad_channel_name(
    client: APIClient,
    default_de: models.DecisionEnvironment,
):
    args = {"limit": 5, "delay": 1}
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.range",
        "source_args": f"{args}",
        "channel_name": "abc-def",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        str(response.data["channel_name"][0])
        == "Channel name can only contain alphanumeric and "
        "underscore characters"
    )


@pytest.mark.django_db
def test_create_event_stream_bad_args(
    client: APIClient,
    default_de: models.DecisionEnvironment,
):
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.range",
        "source_args": "gobbledegook",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    result = response.data
    assert (
        str(result["source_args"][0])
        == "The input field must be a YAML object (dictionary)"
    )


@pytest.mark.django_db
def test_create_event_stream_empty_args(
    client: APIClient,
    default_de: models.DecisionEnvironment,
):
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.generic",
        "decision_environment_id": default_de.id,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["source_args"][0] == "This field is required."


@pytest.mark.django_db
def test_create_event_stream_bad_de(client: APIClient):
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.generic",
        "decision_environment_id": 99999,
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    result = response.data
    assert (
        str(result["decision_environment_id"][0])
        == "DecisionEnvironment with id 99999 does not exist"
    )


@pytest.mark.django_db
def test_create_event_stream_no_de(
    client: APIClient,
):
    data_in = {
        "name": "test_event_stream",
        "source_type": "ansible.eda.generic",
    }
    response = client.post(f"{api_url_v1}/event-streams/", data=data_in)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    result = response.data
    assert result["decision_environment_id"][0] == "This field is required."


@pytest.mark.django_db
def test_list_event_stream_instances(
    client: APIClient,
    default_de: models.DecisionEnvironment,
    default_user: models.User,
):
    args = {"limit": 5, "delay": 1}
    event_stream = models.EventStream.objects.create(
        name="test-event_stream-1",
        source_type="ansible.eda.range",
        source_args=args,
        user=default_user,
        decision_environment_id=default_de.id,
    )

    instances = models.RulebookProcess.objects.bulk_create(
        [
            models.RulebookProcess(
                name="test-activation-instance-1",
                event_stream=event_stream,
                parent_type=ProcessParentType.EVENT_STREAM,
            ),
            models.RulebookProcess(
                name="test-activation-instance-1",
                event_stream=event_stream,
                parent_type=ProcessParentType.EVENT_STREAM,
            ),
        ]
    )
    response = client.get(
        f"{api_url_v1}/event-streams/{event_stream.id}/instances/"
    )
    data = response.data["results"]
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(instances)
    assert data[0]["name"] == instances[0].name
    assert data[1]["name"] == instances[1].name
