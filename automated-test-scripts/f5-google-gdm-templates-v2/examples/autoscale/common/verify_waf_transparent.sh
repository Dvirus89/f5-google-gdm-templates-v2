#  expectValue = "Succeeded"
#  scriptTimeout = 3
#  replayEnabled = true
#  replayTimeout = 60

# get app address
APP_ADDRESS=$(gcloud compute forwarding-rules describe <UNIQUESTRING>-fr0-fr --region=<REGION> --format json | jq -r .IPAddress)
echo "APP_ADDRESS: ${APP_ADDRESS}"

# confirm app is available
ACCEPTED_RESPONSE=$(curl -vv http://${APP_ADDRESS})
echo "ACCEPTED_RESPONSE: ${ACCEPTED_RESPONSE}"

# try something illegal (enforcement mode should be set to blocking by default)
REJECTED_RESPONSE=$(curl -vv -X DELETE http://${APP_ADDRESS})
echo "REJECTED_RESPONSE: ${REJECTED_RESPONSE}"

if echo $ACCEPTED_RESPONSE | grep -q "Demo App" && echo $REJECTED_RESPONSE | grep -q "404"; then
    echo "Succeeded"
else
    echo "Failed"
fi
