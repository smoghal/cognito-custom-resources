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
    Creates a custom user pool domain for the cognito authentication endpoint.
    This endpoint needs to be unique. To update it,
    the existing one needs to be
    deleted first before a new one can be created.

    """
    logger.debug("Creating cognito domain..")

    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    domain = resource_properties.get("CognitoDomainPrefix")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        client.create_user_pool_domain(
            Domain=domain,
            UserPoolId=user_pool_id
        )
    except Exception as err:
        logger.error("exception occured: {}".format(err))
        raise ValueError("unable to create cognito domain: {}".format(err))

    logger.debug("Finished creating cognito domain..")

    physical_resource_id = domain
    return physical_resource_id

@helper.update
def update(event, context):
    """
    Since Cognito user pool domain does not support direct update,
    we delete the existing one and
    create a new one.

    """
    logger.debug("Updating cognito domain..")

    resource_properties = event["ResourceProperties"]

    user_pool_id = resource_properties.get("UserPoolId")
    domain = resource_properties.get("CognitoDomainPrefix")
    cognito_region = resource_properties.get("CognitoRegion")

    client = boto3.client("cognito-idp", region_name=cognito_region)

    if domain is not None:
        try:
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
            return physical_resource_id

        except Exception as err:
            logger.error("exception occured: {}".format(err))
            raise ValueError("unable to update cognito domain: {}".format(err))

    else:
        raise ValueError(
            "CognitoDomainPrefix is required when creating a UserPool Domain.")

@helper.delete
def delete(event, context):
    """
    Delete the specified Cognito user pool domain

    """
    logger.debug("Deleting cognito domain..")

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
