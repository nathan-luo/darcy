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
# Connect to EC2 instance and execute commands

# Add -t to force pseudo-terminal allocation for screen

ssh -i temp_key.pem -t "ec2-user@$EC2_HOST" << 'EOF'
# -----IN EC2 INSTANCE -----

# AI : Navigate to the project directory
cd darcy

# AI : Kill any existing instances of the application
# Use pkill -f to match the full command line
pkill -f "run.py --mode production" || true # Use '|| true' to prevent script exit if no process is found

# AI : Synchronize dependencies
uv sync

# AI : Run the application in the background using nohup, redirecting output
nohup uv run run.py --mode production > darcy.log 2>&1 &

# AI : Exit the SSH session immediately after launching the background process
exit
EOF


# -----OUT OF EC2 INSTANCE -----






# ------------------------------------------------------------------------------------------------
# cleanup

rm temp_key.pem || true        # Clean up the temporary file
