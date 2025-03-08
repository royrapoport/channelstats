# channelstats

## Minimum Requirements

Download the local version of DynamoDB ( https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html ) and run it

`pip3 install -r requirements.txt`

`aws configure`

Then run ./bootstrap

This will take a while as it downloads about two months of data.

Then you can start playing with report_generator.py

## Some Files You'll Need

If you want to slurp things from Slack, you'll need a slack_token.py file that looks like this:
```
read_token = "xox[pb]-RESTOFMYTOKEN..."
post_token = "xox[pb]-..."
```

read_token and post_token can be the same -- we allow you to specify different ones because if you use a bot token for post_token messages will look a little cleaner, but if you use a bot token for read_token, the bot will need to be in every public channel.  One easy solution to this is using the xoxp (user) token for read_token and xoxb (bot) token for write_token

And then you'll want to tweak config.py as appropriate
