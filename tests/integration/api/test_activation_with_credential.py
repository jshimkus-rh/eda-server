#  Copyright 2023 Red Hat, Inc.
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
from typing import Any, Dict

import pytest
import yaml
from rest_framework import status
from rest_framework.test import APIClient

from aap_eda.api.constants import EDA_SERVER_VAULT_LABEL
from aap_eda.api.serializers.activation import is_activation_valid
from aap_eda.core import enums, models
from aap_eda.core.enums import DefaultCredentialType
from aap_eda.core.utils.credentials import inputs_to_store
from aap_eda.core.utils.crypto.base import SecretValue
from tests.integration.constants import api_url_v1

OVERLAP_EXTRA_VAR = """
---
sasl_plain_username: demo
sasl_plain_password: secret
"""

KAFKA_INPUTS = {
    "fields": [
        {"id": "certfile", "type": "string", "label": "Certificate File"},
        {
            "id": "keyfile",
            "type": "string",
            "label": "Key File",
            "secret": True,
        },
        {"id": "password", "type": "string", "label": "Password"},
        {
            "id": "sasl_username",
            "type": "string",
            "label": "SASL User Name",
        },
        {
            "id": "sasl_password",
            "type": "string",
            "label": "SASL Password",
            "secret": True,
        },
    ]
}


INJECTORS = {
    "extra_vars": {
        "keyfile": "{{ keyfile |default(None)}}",
        "certfile": "{{ certfile|default(None) }}",
        "password": "{{ password |default(None)}}",
        "sasl_plain_password": "{{ sasl_password |default(None)}}",
        "sasl_plain_username": "{{ sasl_username |default(None)}}",
    }
}


@pytest.fixture
def kafka_credential_type() -> models.CredentialType:
    return models.CredentialType.objects.create(
        name="type1", inputs=KAFKA_INPUTS, injectors=INJECTORS
    )


@pytest.mark.parametrize(
    ("inputs", "result"),
    [
        ({"username": "adam", "password": "secret"}, True),
        ({"oauth_token": "valid_token"}, True),
        (
            {"username": "adam", "password": "secret", "oauth_token": "token"},
            True,
        ),
        ({"username": "adam", "oauth_token": "token"}, True),
        ({"password": "secret", "oauth_token": "token"}, True),
        ({}, False),
        ({"username": "adam"}, False),
        ({"password": "secret"}, False),
    ],
)
@pytest.mark.django_db
def test_validate_for_aap_credential(
    default_activation: models.Activation,
    inputs,
    result,
    preseed_credential_types,
):
    aap_credential_type = models.CredentialType.objects.get(
        name=DefaultCredentialType.AAP,
    )
    credential = models.EdaCredential.objects.create(
        name="test_eda_credential",
        inputs=inputs,
        managed=False,
        credential_type_id=aap_credential_type.id,
    )
    default_activation.eda_credentials.add(credential)

    valid, _ = is_activation_valid(default_activation)
    assert valid is result


@pytest.mark.django_db
def test_is_activation_valid_with_token_and_run_job_template(
    default_decision_environment: models.DecisionEnvironment,
    default_rulebook_with_run_job_template: models.Rulebook,
    default_project: models.Project,
    default_user_awx_token: models.AwxToken,
    default_user: models.User,
    preseed_credential_types,
):
    activation = models.Activation.objects.create(
        name="test",
        description="test activation",
        rulebook_id=default_rulebook_with_run_job_template.id,
        decision_environment_id=default_decision_environment.id,
        project_id=default_project.id,
        awx_token_id=default_user_awx_token.id,
        user_id=default_user.id,
    )

    valid, _ = is_activation_valid(activation)
    assert valid is True


@pytest.mark.django_db
def test_is_activation_valid_with_aap_credential_and_run_job_template(
    default_activation: models.Activation,
    preseed_credential_types,
):
    aap_credential_type = models.CredentialType.objects.get(
        name=DefaultCredentialType.AAP,
    )
    credential = models.EdaCredential.objects.create(
        name="test_eda_credential",
        inputs={"username": "adam", "password": "secret"},
        managed=False,
        credential_type_id=aap_credential_type.id,
    )

    default_activation.eda_credentials.add(credential)

    valid, _ = is_activation_valid(default_activation)
    assert valid is True


@pytest.mark.django_db
def test_is_activation_valid_with_run_job_template_and_no_token_no_credential(
    default_decision_environment: models.DecisionEnvironment,
    default_rulebook_with_run_job_template: models.Rulebook,
    default_project: models.Project,
    default_user: models.User,
    preseed_credential_types,
):
    activation = models.Activation.objects.create(
        name="test",
        description="test activation",
        rulebook_id=default_rulebook_with_run_job_template.id,
        decision_environment_id=default_decision_environment.id,
        project_id=default_project.id,
        user_id=default_user.id,
    )

    valid, message = is_activation_valid(activation)

    assert valid is False
    assert (
        "The rulebook requires an Awx Token or RH AAP credential."
    ) in message


@pytest.mark.django_db
def test_is_activation_valid_with_updated_credential(
    default_activation: models.Activation,
    default_organization: models.Organization,
    user_credential_type: models.CredentialType,
    admin_client: APIClient,
    preseed_credential_types,
):
    credential = models.EdaCredential.objects.create(
        name="eda-credential",
        inputs={
            "var_1": "adam",
            "var_2": "secret",
            "sasl_username": "adam",
            "sasl_password": "secret",
        },
        credential_type_id=user_credential_type.id,
        organization=default_organization,
    )
    default_activation.eda_credentials.add(credential)

    response = admin_client.post(
        f"{api_url_v1}/activations/{default_activation.id}/restart/"
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    default_activation.refresh_from_db()
    extra_var = yaml.safe_load(default_activation.extra_var)
    assert extra_var["sasl_username"] == "adam"
    assert extra_var["sasl_password"] == "secret"


@pytest.mark.parametrize(
    ("credential_type", "status_code"),
    [
        (
            enums.DefaultCredentialType.VAULT,
            status.HTTP_201_CREATED,
        ),
        (
            enums.DefaultCredentialType.AAP,
            status.HTTP_201_CREATED,
        ),
        (
            enums.DefaultCredentialType.GPG,
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            enums.DefaultCredentialType.REGISTRY,
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            enums.DefaultCredentialType.SOURCE_CONTROL,
            status.HTTP_400_BAD_REQUEST,
        ),
    ],
)
@pytest.mark.django_db
def test_create_activation_with_eda_credentials(
    admin_client: APIClient,
    activation_payload: Dict[str, Any],
    kafka_credential_type: models.CredentialType,
    preseed_credential_types,
    credential_type,
    status_code,
):
    credential_type = models.CredentialType.objects.get(name=credential_type)

    credential = models.EdaCredential.objects.create(
        name="eda-credential",
        description="Default Credential",
        credential_type=credential_type,
        inputs=inputs_to_store(
            {"username": "dummy-user", "password": "dummy-password"}
        ),
    )
    kafka_eda_credential = models.EdaCredential.objects.create(
        name="kafka-eda-credential",
        inputs=inputs_to_store(
            {"sasl_username": "adam", "sasl_password": "secret"},
        ),
        credential_type=kafka_credential_type,
    )
    test_activation = {
        "name": "test_activation",
        "decision_environment_id": activation_payload[
            "decision_environment_id"
        ],
        "rulebook_id": activation_payload["rulebook_id"],
        "eda_credentials": [credential.id, kafka_eda_credential.id],
    }

    response = admin_client.post(
        f"{api_url_v1}/activations/", data=test_activation
    )
    assert response.status_code == status_code

    if status_code == status.HTTP_201_CREATED:
        data = response.data
        assert len(data["eda_credentials"]) == 2

        activation = models.Activation.objects.filter(id=data["id"]).first()

        assert activation.eda_system_vault_credential is not None
        assert activation.eda_system_vault_credential.name.startswith(
            EDA_SERVER_VAULT_LABEL
        )
        assert activation.eda_system_vault_credential.managed is True
        assert isinstance(
            activation.eda_system_vault_credential.inputs, SecretValue
        )

        assert (
            activation.eda_system_vault_credential.credential_type is not None
        )
        credential_type = (
            activation.eda_system_vault_credential.credential_type
        )
        assert credential_type.name == DefaultCredentialType.VAULT
    else:
        assert (
            "The type of credential can not be one of ['Container Registry', "
            "'GPG Public Key', 'Source Control']"
            in response.data["eda_credentials"]
        )


@pytest.mark.django_db
def test_create_activation_with_key_conflict(
    admin_client: APIClient,
    default_decision_environment: models.DecisionEnvironment,
    default_rulebook: models.Rulebook,
    kafka_credential_type: models.CredentialType,
    preseed_credential_types,
):
    test_activation = {
        "name": "test_activation",
        "decision_environment_id": default_decision_environment.id,
        "rulebook_id": default_rulebook.id,
        "extra_var": OVERLAP_EXTRA_VAR,
    }

    test_eda_credential = models.EdaCredential.objects.create(
        name="eda-credential",
        inputs={"sasl_username": "adam", "sasl_password": "secret"},
        credential_type_id=kafka_credential_type.id,
    )
    test_activation["eda_credentials"] = [test_eda_credential.id]

    response = admin_client.post(
        f"{api_url_v1}/activations/", data=test_activation
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Key: sasl_plain_password already exists "
        "in extra var. It conflicts with credential type: type1. "
        "Please check injectors." in response.data["non_field_errors"]
    )


@pytest.mark.django_db
def test_create_activation_with_conflict_credentials(
    admin_client: APIClient,
    activation_payload: Dict[str, Any],
    user_credential_type: models.CredentialType,
    preseed_credential_types,
):
    test_activation = {
        "name": "test_activation",
        "decision_environment_id": activation_payload[
            "decision_environment_id"
        ],
        "rulebook_id": activation_payload["rulebook_id"],
    }

    eda_credentials = models.EdaCredential.objects.bulk_create(
        [
            models.EdaCredential(
                name="credential-1",
                inputs={"sasl_username": "adam", "sasl_password": "secret"},
                credential_type_id=user_credential_type.id,
            ),
            models.EdaCredential(
                name="credential-2",
                inputs={"sasl_username": "bearny", "sasl_password": "demo"},
                credential_type_id=user_credential_type.id,
            ),
        ]
    )

    eda_credential_ids = [credential.id for credential in eda_credentials]
    test_activation["eda_credentials"] = eda_credential_ids

    response = admin_client.post(
        f"{api_url_v1}/activations/", data=test_activation
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Key: sasl_password already exists "
        "in extra var. It conflicts with credential type: user_type. "
        "Please check injectors." in response.data["non_field_errors"]
    )


@pytest.mark.django_db
def test_create_activation_without_extra_vars_single_credential(
    admin_client: APIClient,
    default_decision_environment: models.DecisionEnvironment,
    default_rulebook: models.Rulebook,
    user_credential_type: models.CredentialType,
    preseed_credential_types,
):
    test_activation = {
        "name": "test_activation",
        "decision_environment_id": default_decision_environment.id,
        "rulebook_id": default_rulebook.id,
        "extra_var": None,
    }

    eda_credential = models.EdaCredential.objects.create(
        name="credential-1",
        inputs={"sasl_username": "adam", "sasl_password": "secret"},
        credential_type_id=user_credential_type.id,
    )

    eda_credential_ids = [eda_credential.id]
    test_activation["eda_credentials"] = eda_credential_ids

    assert not test_activation["extra_var"]
    response = admin_client.post(
        f"{api_url_v1}/activations/", data=test_activation
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["extra_var"]
    extra_var = yaml.safe_load(response.data["extra_var"])
    assert extra_var["sasl_username"] == "adam"
    assert extra_var["sasl_password"] == "secret"


@pytest.mark.django_db
def test_create_activation_without_extra_vars_duplicate_credentials(
    admin_client: APIClient,
    default_decision_environment: models.DecisionEnvironment,
    default_rulebook: models.Rulebook,
    user_credential_type: models.CredentialType,
    preseed_credential_types,
):
    test_activation = {
        "name": "test_activation",
        "decision_environment_id": default_decision_environment.id,
        "rulebook_id": default_rulebook.id,
    }

    eda_credentials = models.EdaCredential.objects.bulk_create(
        [
            models.EdaCredential(
                name="credential-1",
                inputs={"sasl_username": "adam", "sasl_password": "secret"},
                credential_type_id=user_credential_type.id,
            ),
            models.EdaCredential(
                name="credential-2",
                inputs={"sasl_username": "bearny", "sasl_password": "demo"},
                credential_type_id=user_credential_type.id,
            ),
        ]
    )

    eda_credential_ids = [credential.id for credential in eda_credentials]
    test_activation["eda_credentials"] = eda_credential_ids

    response = admin_client.post(
        f"{api_url_v1}/activations/", data=test_activation
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Key: sasl_password already exists in extra var. It conflicts with"
        " credential type: user_type. Please check injectors."
        in response.data["non_field_errors"]
    )
