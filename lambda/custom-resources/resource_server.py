__version__ = '0.1.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

import boto3
import crhelper


# initialise logger
logger = crhelper.log_config({"RequestId": "CONTAINER_INIT"})
logger.info('Logging configured')


def create(event, context):
    """
    Creates a custom resource server to manage oauth scopes

    """
    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    identifier = event["ResourceProperties"].get("Identifier")
    name = event["ResourceProperties"].get("Name")
    scopes = event["ResourceProperties"].get("Scopes")
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=identifier,
        Name=name,
        Scopes=scopes
    )

    physical_resource_id = identifier
    response_data = {}
    return physical_resource_id, response_data


def update(event, context):
    """
    Update a custom resource server with custom scopes

    """
    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    identifier = event["ResourceProperties"].get("Identifier")
    name = event["ResourceProperties"].get("Name")
    scopes = event["ResourceProperties"].get("Scopes")
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        client.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=identifier
        )
        client.update_resource_server(
            UserPoolId=user_pool_id,
            Identifier=identifier,
            Name=name,
            Scopes=scopes
        )
    except Exception:
        logger.debug("Resource server {} does not exist in User pool {}."
                     .format(identifier, user_pool_id))
        client.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=identifier,
            Name=name,
            Scopes=scopes
        )

    physical_resource_id = event['PhysicalResourceId']
    response_data = {}
    return physical_resource_id, response_data


def delete(event, context):
    """
    Delete a resource server.

    """
    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    identifier = event['PhysicalResourceId']
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        client.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=identifier
        )
    except Exception:
        logger.debug("Unable to find resource server to delete. identifier: {}"
                     .format(identifier))
        return

    client.delete_resource_server(
        UserPoolId=user_pool_id,
        Identifier=identifier
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
