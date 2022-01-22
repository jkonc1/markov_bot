CREATE TABLE IF NOT EXISTS users(
    UserID INTEGER primary key,
    DiscordUserID TEXT,
    EdupageUserName TEXT,
    EdupagePassword TEXT,
    EdupageServer TEXT
);

CREATE TABLE IF NOT EXISTS subscriptions(
    SubscriptionID INTEGER PRIMARY KEY,
    ChannelID TEXT,
    SourceName TEXT,
    DestinationName TEXT,
    Type TEXT,
    Account integer not null,
    foreign key(Account) references users(UserID)
);

CREATE TABLE IF NOT EXISTS notifications(
    NotificationID INTEGER primary key,
    DiscordUserID TEXT,
    Website TEXT,
    Regex TEXT,
    ChannelID TEXT
);