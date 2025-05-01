


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

# SSH requires strict permissions
chmod 600 temp_key.pem || true  


# ------------------------------------------------------------------------------------------------
# Transfer the .env file to the EC2 instance



REMOTE_PATH="/home/ec2-user/darcy/.env"
scp -i temp_key.pem ./.env "ec2-user@$EC2_HOST:$REMOTE_PATH"

REMOTE_PATH="/home/ec2-user/llmgine/.env"
scp -i temp_key.pem ./.env "ec2-user@$EC2_HOST:$REMOTE_PATH"


# ------------------------------------------------------------------------------------------------
# Connect to EC2 instance

ssh -i temp_key.pem "ec2-user@$EC2_HOST"





# -----IN EC2 INSTANCE -----


screen -r

cd darcy
uv sync
uv run run.py --production
exit



# -----OUT OF EC2 INSTANCE -----






# ------------------------------------------------------------------------------------------------
# cleanup

rm temp_key.pem || true        # Clean up the temporary file
