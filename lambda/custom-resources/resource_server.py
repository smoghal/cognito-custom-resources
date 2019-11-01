__version__ = '0.1.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

import boto3
from crhelper import CfnResource
import logging


logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

@helper.create
def create(event, context):
    """
    Creates a custom resource server to manage oauth scopes

    """
    logger.debug("Creating resource server..")

    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    identifier = event["ResourceProperties"].get("Identifier")
    name = event["ResourceProperties"].get("Name")
    scopes = event["ResourceProperties"].get("Scopes")
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        client.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=identifier,
            Name=name,
            Scopes=scopes
        )
    except Exception as err:
        logger.error("exception occured: {}".format(err))
        raise ValueError("unable to create resource server: {}".format(err))

    logger.debug("Finished creating resource server..")

    physical_resource_id = identifier
    return physical_resource_id

@helper.update
def update(event, context):
    """
    Update a custom resource server with custom scopes

    """
    logger.debug("Updating resource server..")

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
    return physical_resource_id


@helper.delete
def delete(event, context):
    """
    Delete a resource server.

    """
    logger.debug("Deleting resource server..")

    user_pool_id = event["ResourceProperties"].get("UserPoolId")
    identifier = event['PhysicalResourceId']
    cognito_region = event["ResourceProperties"].get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    logger.debug("user_pool_id: {}".format(user_pool_id))
    logger.debug("identifier: {}".format(identifier))
    logger.debug("cognito_region: {}".format(cognito_region))

    try:
        logger.debug("Describing resource server..")
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

    logger.debug("Finished deleting resource server..")

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
