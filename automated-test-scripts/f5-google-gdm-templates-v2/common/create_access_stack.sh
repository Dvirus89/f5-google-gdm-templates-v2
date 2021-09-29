#  expectValue = "completed successfully"
#  scriptTimeout = 5
#  replayEnabled = false
#  replayTimeout = 0

template_url=<ACCESS TEMPLATE URL>
echo "template_url = $template_url"
template_file=$(basename "$template_url")
echo "template_file = $template_file"
tmpl_file="/tmp/$template_file"
echo "tmpl_file = $tmpl_file"
rm -f $tmpl_file

curl -k $template_url -o $tmpl_file

# Run GDM Access template
properties="uniqueString:'<UNIQUESTRING>',solutionType:'<SOLUTION TYPE>',storageName:'<STORAGE NAME>',secretId:'<SECRET ID>'"
echo $properties
gcloud deployment-manager deployments create <ACCESS STACK NAME> --template $tmpl_file --labels "delete=true" --properties $properties

# clean up file on disk
rm -f $tmpl_file