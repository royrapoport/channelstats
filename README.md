# channelstats

Minimum requirements:

Download the local version of DynamoDB ( https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html ) and run it

Then run ./bootstrap

This will take a while as it downloads about two months of data.

Then you can start playing with report_generator.py

# Notes

You will need (at least):
  - `awscli` installed (`pip3 install awscli --upgrade --user`) and configured (`aws configure`)
  - a Slack legacy token in `slack_token.py` (`token = "xoxp-...."`)
