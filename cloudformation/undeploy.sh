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
# FUNCTIONS

# this function checks if a template exists by using "describe" cli
# command.  It continues to check for template for 3 minutes.  If the
# template still exists after 3 minutes, the function returns with a
# non-zero exit code.  Otherwise, the function returns 0 code indicating
# that template does not exist.
checkTemplate() {

	stack_name=$1
	counter=0
	wait_time="5s"
	wait_threshold=36	# wait threshold before breaking the while loop
	    				# 36 counts = 180s / 5s
	STACK_OUTPUT_FILE="/tmp/$$.output.${stack_name}"

	while [ 1 ]; do
		# describe stack
		"${AWS_CLI_BIN}" cloudformation describe-stacks \
			--output text \
			--stack-name "${stack_name}" \
			--region "${AWS_REGION}" \
			--profile "${AWS_PROFILE}" >& "$STACK_OUTPUT_FILE"
		# capture return value
		ret_value=$?
		# if return value is non-zero, that means stack does not exist
		# so break out of loop
		if [ $ret_value -ne 0 ]; then
			#cat $STACK_OUTPUT_FILE
			rm -rf /tmp/$$.*
			return 0
		fi

		# otherwise if return value is zero, stack still exists or
		# is in the process of being deleted,
		# so wait for 5s and repeat the loop
		sleep ${wait_time}

		# however, if it is over 2mins (120s / 5s = 24 counts)
		# then exit out of the loop
		# we don't want to loop indefinitely
		counter=`expr $counter + 1`
		if [ $counter -ge $wait_threshold ]; then
			break
		fi
	done

	# if loop stopped because of counter threshold breach
	# then exit from this function
	if [ $counter -ge $wait_threshold ]; then
		return 1
	fi

	# otherwise return 0 (though this statement should never execute)
	return 0
}

#####################################################################
# TEMPLATE PARAMETERS

# stack name and other bootstrap parameters
stack_name_s3=dpm-scd-infra-s3
stack_name_cognito=dpm-scd-infra-cognito


#####################################################################
# EMPTY S3 Bucket first

# grab bucket name
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
echo "Emtying s3 bucket ${INFRA_BUCKET_NAME}..."
"${AWS_CLI_BIN}" s3 rm \
    "s3://${INFRA_BUCKET_NAME}" \
	--recursive \
    --region "${AWS_REGION}" \
    --profile "${AWS_PROFILE}" >& /tmp/$$.s3-rm.gluejob
if [ $? -ne 0 ]; then
    echo "Error during s3 copy operation"
    cat /tmp/$$.s3-rm.gluejob
    rm -rf /tmp/$$.*
    exit 3
fi


#####################################################################
# DELETE TEMPLATES

# build string containing all stacks and reverse the stack dependancies
stacks="${stack_name_cognito} ${stack_name_s3}"

# iterate over stacks and delete them
for stack_name in ${stacks}; do
    echo "Deleting ${stack_name} stack..."
    "${AWS_CLI_BIN}" cloudformation delete-stack \
        --stack-name "${stack_name}" \
        --region "${AWS_REGION}" \
        --profile "${AWS_PROFILE}" >& /tmp/$$.delete.$stack_name

	# check if template was successfully deleted
	checkTemplate ${stack_name}
	if [ $? -ne 0 ]; then
		echo ">> stack deletion was not successful. check CFN console or re-run this script."
	fi

done

#####################################################################
# CLEAN UP
rm -rf /tmp/$$.*