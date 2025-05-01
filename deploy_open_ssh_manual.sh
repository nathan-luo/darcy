# THIS IS HELLA JANK AND IM SORRY
# WE SHOULD HAVE A BETTER METHOD OF AUTOMATED DEPLOYMENT



# ------------------------------------------------------------------------------------------------
# setup env export

set -a
source .env
set +a

# check not empty
echo "$EC2_PRIVATE_KEY"

# write to a file, strings dont work
echo "$EC2_PRIVATE_KEY" > temp_key.pem
cat temp_key.pem

# SSH requires strict permissions
chmod 600 temp_key.pem || true



# assert cat temp_key.pem is not empty
if [ -z "$EC2_PRIVATE_KEY" ]; then
    echo "Error: EC2_PRIVATE_KEY is empty"
fi



# assert cat $EC2_HOST is not empty
if [ -z "$EC2_HOST" ]; then
    echo "Error: EC2_HOST is empty"
fi


# ------------------------------------------------------------------------------------------------
# Connect to EC2 instance and execute commands

# Add -t to force pseudo-terminal allocation for screen


ssh -vvv -i temp_key.pem "ec2-user@$EC2_HOST"




# -----OUT OF EC2 INSTANCE -----



# ------------------------------------------------------------------------------------------------
# cleanup

rm temp_key.pem || true        # Clean up the temporary file
