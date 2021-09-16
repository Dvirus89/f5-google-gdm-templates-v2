#  expectValue = "Successful"
#  scriptTimeout = 3
#  replayEnabled = true
#  replayTimeout = 180


TMP_DIR=/tmp/<DEWPOINT JOB ID>

# source test functions
source ${TMP_DIR}/test_functions.sh

if [[ <PROVISION PUBLIC IP> == True ]]; then
    IP=$(get_mgmt_ip <UNIQUESTRING>-bigip1 <AVAILABILITY ZONE> public)
    echo "IP: ${IP}"
    ssh-keygen -R $IP 2>/dev/null
    RESPONSE=$(sshpass -p <UNIQUESTRING>-<INSTANCE NAME> ssh -o StrictHostKeyChecking=no quickstart@${IP} "bash -c 'cat /var/log/cloud/bigIpRuntimeInit.log | grep \"All operations finished successfully\"'")
else
    BASTION_IP=$(get_bastion_ip <UNIQUESTRING>-bastion <AVAILABILITY ZONE>)
    IP=$(get_mgmt_ip <UNIQUESTRING>-bigip1 <AVAILABILITY ZONE> private)
    echo "BASTION_IP: ${BASTION_IP}"
    echo "IP: ${IP}"
    ssh-keygen -R $BASTION_IP 2>/dev/null
    RESPONSE=$(ssh -o "StrictHostKeyChecking no" -o ConnectTimeout=5 -i /etc/ssl/private/dewpt_private.pem -o ProxyCommand="ssh -o 'StrictHostKeyChecking no' -o ConnectTimeout=7 -i /etc/ssl/private/dewpt_private.pem -W %h:%p dewpt@${BASTION_IP}" admin@"${IP}" "bash -c 'cat /var/log/cloud/bigIpRuntimeInit.log | grep \"All operations finished successfully\"'")
fi

if echo $RESPONSE  | grep -Eq "All operations finished successfully"; then
    echo "IP ADDRESS: ${IP} is onboarded. Incrementing test counter..."
    ((count=count+1))
fi
echo "Test counter: ${count}"

if [[ $count == 1 ]]; then
    echo "Successful"
fi