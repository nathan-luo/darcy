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


# ------------------------------------------------------------------------------------------------
# Connect to EC2 instance and execute commands

# Add -t to force pseudo-terminal allocation for screen


ssh -i temp_key.pem "ec2-user@$EC2_HOST"




# -----OUT OF EC2 INSTANCE -----



# ------------------------------------------------------------------------------------------------
# cleanup

rm temp_key.pem || true        # Clean up the temporary file
