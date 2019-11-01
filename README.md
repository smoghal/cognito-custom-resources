# Overview

`UPDATE: CloudFormation now natively supports creation of Cognito Domain, Resources and Client ids.  So this code should be used for references purposes only.`

This repository contains sample Lambda functions that handle creating Cognito resources that are currently not supported by CloudFormation.  These Cognito resources are:

- Cognito Domain
- Cognito Resource Server
- Cognito AppClient Id

As the changes are made to the Cognito CloudFormation templates, custom resource Lambda function takes care of automatically updating (creating/deleting) the underlying resources (listed above).

The code uses `crhelper` library from [aws blog](https://aws.amazon.com/blogs/infrastructure-and-automation/aws-cloudformation-custom-resource-creation-with-python-aws-lambda-and-crhelper/) post.

## Deployment

In order to deploy the custom resources, run `deploy.sh` script in cloudformation folder.  This script only executes when following environment variables are set:

- AWS_PROFILE
- AWS_REGION
- AWS_CLI_BIN

Set `AWS_PROFILE` environment to point to your AWS account.  Set `AWS_REGION` appropriately for your account.  Finally, set `AWS_CLI_BIN` to the fully qualified path of your AWS CLI binary.

## Tear-down

The tear-down script is available in `cloudformation/undeploy.sh`.  Simply execute this script to undeploy all stacks.  Make sure that infra S3 buckets are empty.
