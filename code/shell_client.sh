url=$1
env=$2
event=$3
string=$4
epoch_seconds=$(date +%s)
payload_string="{\"events\": [{\"name\": \"$event\", \"env\": \"$env\", \"time\": \"$epoch_seconds\", \"data\": \"$string\"}]}"
curl -X POST -H "Content-Type:application/json" -d "$payload_string" "$url/affirmative/store"
