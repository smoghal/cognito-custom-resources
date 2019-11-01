__version__ = '0.1.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

import boto3
from crhelper import CfnResource
import logging
import re

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

@helper.create
def create(event, context):
    """
    Creates a user pool client with the specified attributes.
    """
    logger.debug("Creating app client..")
    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    app_client_name = resource_properties.get("AppClientName")
    scope = resource_properties.get("CustomScope")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
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

        logger.debug("Finished creating app client..")

        physical_resource_id = response.get("UserPoolClient").get("ClientId")
        return physical_resource_id

    except Exception as err:
        logger.error("exception occured: {}".format(err))
        raise ValueError("unable to create app client: {}".format(err))

@helper.update
def update(event, context):
    """
    Updates a user pool client with the specified attributes.
    Note if in the future we want to add ability to
    update the client's other properties,
    Add them in the update_user_pool_client call here.
    """
    logger.debug("Updating app client..")

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
        return physical_resource_id

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
        return physical_resource_id

@helper.delete
def delete(event, context):
    """
    Delete a user pool client.

    """
    logger.debug("Deleting app client..")

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

    logger.debug("Finished deleting app client..")

    return

@helper.poll_create
def poll_create(event, context):
    logger.info("Create polling..")
    # Return a resource id or True to indicate that creation is complete. if True is returned an id
    # will be generated
    return True

def handler(event, context):
    """
    Main handler function, passes off it's work to crhelper's cfn_handler
    """
    helper(event, context)
