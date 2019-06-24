__version__ = '0.1.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

import boto3
import re
import crhelper

# initialise logger
logger = crhelper.log_config({"RequestId": "CONTAINER_INIT"})
logger.info('Logging configured')


def create(event, context):
    """
    Creates a user pool client with the specified attributes.
    """
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    app_client_name = resource_properties.get("AppClientName")
    scope = resource_properties.get("CustomScope")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    response = client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=app_client_name,
        GenerateSecret=True,
        RefreshTokenValidity=30,
        AllowedOAuthFlows=[
            'client_credentials',
        ],
        AllowedOAuthScopes=[
            scope
        ],
        AllowedOAuthFlowsUserPoolClient=True
    )

    physical_resource_id = response.get("UserPoolClient").get("ClientId")
    response_data = {}
    return physical_resource_id, response_data


def update(event, context):
    """
    Updates a user pool client with the specified attributes.
    Note if in the future we want to add ability to
    update the client's other properties,
    Add them in the update_user_pool_client call here.
    """
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    app_client_name = resource_properties.get("AppClientName")
    scope = resource_properties.get("CustomScope")
    cognito_region = resource_properties.get("CognitoRegion")
    client_id = event['PhysicalResourceId']

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id)

        client.update_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            ClientName=app_client_name,
            AllowedOAuthFlows=[
                'client_credentials',
            ],
            AllowedOAuthScopes=[
                scope
            ],
            AllowedOAuthFlowsUserPoolClient=True
        )
        physical_resource_id = event['PhysicalResourceId']
    except Exception:
        response = client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=app_client_name,
            GenerateSecret=True,
            RefreshTokenValidity=30,
            AllowedOAuthFlows=[
                'client_credentials',
            ],
            AllowedOAuthScopes=[
                scope
            ],
            AllowedOAuthFlowsUserPoolClient=True
        )
        physical_resource_id = response.get("UserPoolClient").get("ClientId")

    response_data = {}
    return physical_resource_id, response_data


def delete(event, context):
    """
    Delete a user pool client.

    """

    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    if not re.match(r'[\w+]+', event.get('PhysicalResourceId')):
        logger.debug("No physical resource to delete. Continue.")

    try:
        client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=event['PhysicalResourceId']
        )
    except Exception:
        logger.debug("Unable to find user pool client to delete. ClientId: {}"
                     .format(event['PhysicalResourceId']))
        return

    client.delete_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=event['PhysicalResourceId']
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
