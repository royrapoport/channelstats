# channelstats

## Minimum requirements

Download the local version of DynamoDB ( https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html ) and run it

Install boto3 and configure it appropriately (likely using `aws configure`)

Then run ./bootstrap

This will take a while as it downloads about two months of data.

Then you can start playing with report_generator.py

## Some files you'll need

If you want to do PDF generation, you'll need a pdfcrowd_token.py file whose format is
```
uname = "MYUSERNAME"
key = "MYTOKEN"
```

If you want to slurp things from Slack, you'll need a slack_token.py file that looks like this:
```
token = "xoxp-RESTOFMYTOKEN"
```

And then you'll want to tweak config.py as appropriate
