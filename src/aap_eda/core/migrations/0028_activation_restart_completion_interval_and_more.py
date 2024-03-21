# Generated by Django 4.2.7 on 2024-03-21 18:43

import django.core.validators
from django.db import migrations, models

import aap_eda.core.models.activation
import aap_eda.core.models.event_stream


class Migration(migrations.Migration):
    dependencies = [
        (
            "core",
            "0027_credentialtype_alter_permission_resource_type_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="activation",
            name="restart_completion_interval",
            field=models.IntegerField(
                default=aap_eda.core.models.activation.RestartCompletionInterval[
                    "MINIMUM"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.activation.RestartCompletionInterval[
                            "MINIMUM"
                        ],
                        message="The restart interval for completions specifies the delay, in seconds, between restarts; it must be an integer greater than or equal to 0 indicating the delay, in seconds, between restarts; system settings = 0, default = 0",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="activation",
            name="restart_failure_interval",
            field=models.IntegerField(
                default=aap_eda.core.models.activation.RestartFailureInterval[
                    "MINIMUM"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.activation.RestartFailureInterval[
                            "MINIMUM"
                        ],
                        message="The restart interval for failures specifies the delay, in seconds, between restarts; it must be an integer greater than or equal to  0 indicating the delay, in seconds, between restarts; system settings = 0, default = 0",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="activation",
            name="restart_failure_limit",
            field=models.IntegerField(
                default=aap_eda.core.models.activation.RestartFailureLimit[
                    "SETTINGS"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.activation.RestartFailureLimit[
                            "MINIMUM"
                        ],
                        message="The restart limit for failiures specifies the limit on repeated attempts to start an activation in the face of failures to do so; it must be an integer greater than or equal to -1; system settings = 0, unlimited restarts = -1, default = 0",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="eventstream",
            name="restart_completion_interval",
            field=models.IntegerField(
                default=aap_eda.core.models.event_stream.RestartCompletionInterval[
                    "MINIMUM"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.event_stream.RestartCompletionInterval[
                            "MINIMUM"
                        ],
                        message="The restart interval for completions specifies the delay, in seconds, between restarts; it must be an integer greater than or equal to 0 indicating the delay, in seconds, between restarts; system settings = 0, default = 0",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="eventstream",
            name="restart_failure_interval",
            field=models.IntegerField(
                default=aap_eda.core.models.event_stream.RestartFailureInterval[
                    "MINIMUM"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.event_stream.RestartFailureInterval[
                            "MINIMUM"
                        ],
                        message="The restart interval for failures specifies the delay, in seconds, between restarts; it must be an integer greater than or equal to  0 indicating the delay, in seconds, between restarts; system settings = 0, default = 0",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="eventstream",
            name="restart_failure_limit",
            field=models.IntegerField(
                default=aap_eda.core.models.event_stream.RestartFailureLimit[
                    "SETTINGS"
                ],
                validators=[
                    django.core.validators.MinValueValidator(
                        limit_value=aap_eda.core.models.event_stream.RestartFailureLimit[
                            "MINIMUM"
                        ],
                        message="The restart limit for failiures specifies the limit on repeated attempts to start an activation in the face of failures to do so; it must be an integer greater than or equal to -1; system settings = 0, unlimited restarts = -1, default = 0",
                    )
                ],
            ),
        ),
    ]
