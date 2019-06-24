__version__ = '0.1.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

import boto3
import crhelper


# initialise logger
logger = crhelper.log_config({"RequestId": "CONTAINER_INIT"})
logger.info('Logging configured')


def create(event, context):
    """
    Creates a custom user pool domain for the cognito authentication endpoint.
    This endpoint needs to be unique. To update it,
    the existing one needs to be
    deleted first before a new one can be created.

    """
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    domain = resource_properties.get("CognitoDomainPrefix")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    client.create_user_pool_domain(
        Domain=domain,
        UserPoolId=user_pool_id
    )

    physical_resource_id = domain
    response_data = {}
    return physical_resource_id, response_data


def update(event, context):
    """
    Since Cognito user pool domain does not support direct update,
    we delete the existing one and
    create a new one.

    """
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    domain = resource_properties.get("CognitoDomainPrefix")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    if domain is not None:
        response = client.describe_user_pool(
            UserPoolId=user_pool_id
        )

        existing_domain = response.get("UserPool").get("Domain")

        if existing_domain is not None:
            client.delete_user_pool_domain(
                Domain=existing_domain,
                UserPoolId=user_pool_id
            )
            print("Domain " + existing_domain + " has been deleted")

        client.create_user_pool_domain(
            Domain=domain,
            UserPoolId=user_pool_id
        )

        physical_resource_id = domain
        response_data = {}
        return physical_resource_id, response_data

    else:
        raise ValueError(
            "CognitoDomainPrefix is required when creating a UserPool Domain.")


def delete(event, context):
    """
    Delete the specified Cognito user pool domain

    """
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    domain = resource_properties.get("CognitoDomainPrefix")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    response = client.describe_user_pool(
        UserPoolId=user_pool_id
    )

    existing_domain = response.get("UserPool").get("Domain")

    if existing_domain == domain:
        client.delete_user_pool_domain(
            Domain=domain,
            UserPoolId=user_pool_id
        )
    return


def handler(event, context):
    """
    Main handler function, passes off it's work to crhelper's cfn_handler
    """
    # update the logger with event info
    global logger
    logger = crhelper.log_config(event)
    return crhelper.cfn_handler(event, context, create, update, delete, logger,
                                False)
