// MongoDB entrypoint script
// - DB name: furretweet
// - Collection name: filtered_tweets
// - Create index on "author_id" field in "filtered_tweets"

db.auth("furretweet", "areallygoodpasswordhere");

db.not_retweeted_tweets.createIndex({ author_id: 1 }, { unique: false });
