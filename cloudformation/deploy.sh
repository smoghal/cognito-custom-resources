#!/bin/sh

#####################################################################
# PREFLIGHT CHECK
if [ -z "${AWS_PROFILE}" -o -z "${AWS_REGION}" -o -z "${AWS_CLI_BIN}" ]; then
    echo "Missing environment variables.  Ensure following environment variables are set"
    echo "  AWS_PROFILE"
    echo "  AWS_REGION"
    echo "  AWS_CLI_BIN"
    exit 1
fi

#####################################################################
# TEMPLATE PARAMETERS

# stack name and other bootstrap parameters
# stack_name_vpc=proj1-cognito-test-infra-vpc
stack_name_s3=proj1-cognito-test-infra-s3
stack_name_cognito=proj1-cognito-test-infra-cognito

# template yaml
#cfn_template_vpc=0-vpc.yaml
cfn_template_s3=1-s3.yaml
cfn_template_cognito=2-cognito.yaml

# parameter - globals
param_global_env_name="dev"
param_global_project_code="proj1-cognito-test"
# parameters - vpc stack
#param_eip_allocation_id=eipalloc-???? # this is created in VPC console before hand (manually)
# parameters - s3
param_s3_infra_bucket_name="proj1-cognito-test-infra"
# parameters - cognito
param_cognito_authname="proj1-cognito-test"
param_cognito_region="${AWS_REGION}"
param_cognito_domain_prefix="proj1-cognito-test"
param_cognito_resource_server_name="proj1-cognito-test"
param_cognito_resource_server_id="proj1-cognito-test"
param_cognito_custom_resource_lambda_loglevel="DEBUG"
# parameters - dynamodb
# lambda folder with requirements.txt
lambda_code_path="../lambda/custom-resources"

#####################################################################
# VALIDATE TEMPALTES

# Perfom validation on all templates present in current directory
AWS_TEMPLATES="?-*.yaml"
ls ${AWS_TEMPLATES} | while read fn; do
    echo "Validating ${fn}"
    # validate CFN template and record output in /tmp/$$.validate.$fn
    "${AWS_CLI_BIN}" cloudformation validate-template \
        --template-body file://${fn} \
        --region "${AWS_REGION}" \
        --profile "${AWS_PROFILE}" >& /tmp/$$.validate.$fn

    # check if there were errors during validation,
    # if so dump the contents of /tmp/$$.validate.$fn
    # clean up the /tmp/$$.* temporary files
    if [ $? -ne 0 ]; then
        echo "ERROR: unable to validate ${fn}"
        cat /tmp/$$.validate.$fn
        rm -rf /tmp/$$.*
        exit 1
    fi
done

# if loop above resulted in an error, then halt deployment and exit
if [ $? -ne 0 ]; then
    exit 1
fi


#####################################################################
# BUILD PYTHON LAMBDA(S)

echo "Building python lambda(s)..."
(
    dist_path="./dist"
    cd "${lambda_code_path}"
    # rebuild python virtual environment
    virtualenv .venv
    pip install -r requirements.txt
    # activate virtual environment
    source .venv/bin/activate
    # rebuild the ./dist folder
    rm -rf "${dist_path}"
    mkdir "${dist_path}"
    cp *.py requirements.txt "${dist_path}"

    echo "Installing dependencies..."
    pip install --target="${dist_path}" -r "${dist_path}/requirements.txt"
) >& /tmp/$$.build

if [ $? -ne 0 ]; then
    echo "Error during build process"
    cat /tmp/$$.build
    rm -rf /tmp/$$.*
    exit 3
fi


#####################################################################
# DEPLOY TEMPLATE - cfn_template_s3

# NOTE: First deploy the infrastructure bucket so it can be used by
# package command below

# deploy cfn_template_s3 template
fn=${cfn_template_s3}
stack_name=${stack_name_s3}
echo "Deploying ${fn} template..."
"${AWS_CLI_BIN}" cloudformation deploy \
    --template-file "${fn}" \
    --stack-name "${stack_name}" \
    --parameter-overrides \
        InfraBucketName="${param_s3_infra_bucket_name}" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" >& /tmp/$$.deploy.$fn
if [ $? -ne 0 ]; then
    echo "Error during deploy operation"
    cat /tmp/$$.deploy.$fn
    rm -rf /tmp/$$.*
    exit 2
fi


#####################################################################
# PACKAGE TEMPLATE
#    This cloudformation step is not needed if there is no
#    CodeUri's in templates

# grab infra bucket name
stack_name=${stack_name_s3}
STACK_OUTPUT_FILE="/tmp/$$.output.${stack_name}"
"${AWS_CLI_BIN}" cloudformation describe-stacks \
    --output text \
    --stack-name "${stack_name}" \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" > "$STACK_OUTPUT_FILE"
if [ $? -ne 0 ]; then
    echo "Error during describe-stacks operation"
    cat /tmp/$STACK_OUTPUT_FILE
    rm -rf /tmp/$$.*
    exit 3
fi
INFRA_BUCKET_NAME=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'InfraBucketName' | awk '{print $5}'`

# package CFN
ls ${AWS_TEMPLATES} | while read fn; do
    echo "Packaging ${fn}..."
    ARTIFACTS_S3_BUCKET="${INFRA_BUCKET_NAME}"
    OUTPUT_FILE="/tmp/$$.package.${fn}"
    aws cloudformation package \
        --template-file "${fn}" \
        --s3-bucket "${ARTIFACTS_S3_BUCKET}" \
        --output-template-file "${OUTPUT_FILE}" \
        --region "${AWS_REGION}" \
        --profile "${AWS_PROFILE}" >& /tmp/$$.package.error.$fn

    # check if there were errors during packaging,
    # if so dump the contents of /tmp/$$.package.error.$fn
    # clean up the /tmp/$$.* temporary files
    if [ $? -ne 0 ]; then
        echo "ERROR: unable to package ${fn}"
        cat /tmp/$$.package.error.$fn
        rm -rf /tmp/$$.*
        exit 1
    fi
done

# if loop above resulted in an error, then halt deployment and exit
if [ $? -ne 0 ]; then
    exit 1
fi



#####################################################################
# DEPLOY TEMPLATE - /tmp/$$.package.${fn}

# deploy cfn_template_cognito template
fn=${cfn_template_cognito}
stack_name=${stack_name_cognito}
OUTPUT_FILE="/tmp/$$.package.${fn}"
TEMPLATE_FILE="${OUTPUT_FILE}"
echo "Deploying ${fn} template..."
"${AWS_CLI_BIN}" cloudformation deploy \
    --template-file "${TEMPLATE_FILE}" \
    --stack-name "${stack_name}" \
    --parameter-overrides \
        Environment="${param_global_env_name}" \
        AuthName="${param_cognito_authname}" \
        CognitoRegion="${param_cognito_region}" \
        CognitoDomainPrefix="${param_cognito_domain_prefix}" \
        CognitoResourceServerName="${param_cognito_resource_server_name}" \
        CognitoResourceServerIdentifier="${param_cognito_resource_server_id}" \
        LoggingLevel="${param_cognito_custom_resource_lambda_loglevel}" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" >& /tmp/$$.deploy.$fn
if [ $? -ne 0 ]; then
    echo "Error during deploy operation"
    cat /tmp/$$.deploy.$fn
    rm -rf /tmp/$$.*
    exit 2
fi


#####################################################################
# DISPLAY TEMPLATE OUTPUTS

# capture and display stack output - stack_name_s3
stack_name=${stack_name_s3}
STACK_OUTPUT_FILE="/tmp/$$.output.${stack_name}"
"${AWS_CLI_BIN}" cloudformation describe-stacks \
    --output text \
    --stack-name "${stack_name}" \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" > "$STACK_OUTPUT_FILE"
if [ $? -ne 0 ]; then
    echo "Error during describe-stacks operation"
    cat /tmp/$STACK_OUTPUT_FILE
    rm -rf /tmp/$$.*
    exit 3
fi
INFRA_BUCKET_NAME=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'InfraBucketName' | awk '{print $5}'`
INFRA_BUCKET_ARN=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'InfraBucketArn' | awk '{print $5}'`
echo "${stack_name} stack output:"
echo "  INFRA_BUCKET_NAME   : $INFRA_BUCKET_NAME"
echo "  INFRA_BUCKET_ARN    : $INFRA_BUCKET_ARN"

# capture and display stack output - stack_name_cognito
stack_name=${stack_name_cognito}
STACK_OUTPUT_FILE="/tmp/$$.output.${stack_name}"
"${AWS_CLI_BIN}" cloudformation describe-stacks \
    --output text \
    --stack-name "${stack_name}" \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" > "$STACK_OUTPUT_FILE"
if [ $? -ne 0 ]; then
    echo "Error during describe-stacks operation"
    cat /tmp/$STACK_OUTPUT_FILE
    rm -rf /tmp/$$.*
    exit 3
fi
USER_POOL_ID=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'UserPoolId' | awk '{print $5}'`
USER_POOL_CLIENT_ID=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'UserPoolClientId' | awk '{print $5}'`
INTERNAL_CLIENT_ID=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'InternalAppClientId' | awk '{print $5}'`
COGNITO_DOMAIN_NAME=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'CognitoDomainName' | awk '{print $5}'`
COGNITO_RESOURCE_SERVER_NAME=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'CognitoResourceServerName' | awk '{print $5}'`
COGNITO_RESOURCE_CUSTOM_SCOPE=`grep '^OUTPUTS' $STACK_OUTPUT_FILE | grep 'CognitoResourceServerCustomScope' | awk '{print $5}'`
echo "${stack_name} stack output:"
echo "  USER_POOL_ID                  : $USER_POOL_ID"
echo "  USER_POOL_CLIENT_ID           : $USER_POOL_CLIENT_ID"
echo "  INTERNAL_CLIENT_ID            : $INTERNAL_CLIENT_ID"
echo "  COGNITO_DOMAIN_NAME           : $COGNITO_DOMAIN_NAME"
echo "  COGNITO_RESOURCE_SERVER_NAME  : $COGNITO_RESOURCE_SERVER_NAME"
echo "  COGNITO_RESOURCE_CUSTOM_SCOPE : $COGNITO_RESOURCE_CUSTOM_SCOPE"


#####################################################################
# CLEAN UP
rm -rf /tmp/$$.*
rm -rf "${lambda_code_path}/dist"