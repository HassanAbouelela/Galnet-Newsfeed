# Galnet Newsfeed
An open source program to get ED galnet news from the [game's website.](https://community.elitedangerous.com/)
 
## Description
Collects, indexes, and searches Galnet News Articles.\
[A discord bot is available](https://discordapp.com/api/oauth2/authorize?client_id=624620325090361354&permissions=379968&scope=bot).

## Requirements
Python\
All requirements in requirements.txt\
[Postgres database](https://www.postgresql.org/) (Just a very basic setup is required. More on that later.)

## Setup
If this is the very first time you are starting this program, you have to run "initalbuild.py". You need to provide it with:
1. Postgres host (localhost if it's a local install, IP if it is on a remote server) + port
2. User that the table will belong to. This user must have the create table permission.
3. Authentication method. This can be ssl, password, or password file.
4. Database to be used. (The user from requirement 2 must have access to this DB.)
5. (Optional) The default name for the table to be created is "Articles", but that can be customized using the table parameter. If it is changed from its default value, all instance of "Articles" in "articlesearch.py" must be changed to the new name.
6. (Optional - Not Recommenced) If you already have a table with all the required columns, you can pass in the name using the table parameter to add the articles. 


"autoinitialbuild.py" is a very basic setup script if you don't know how to do the previously mentioned steps. This will create a table on the machine it is run on. Postgres must be pre installed however. More details in the postgres section. If you use this file you will need: the "asyncio" module.

If you used the "autoinitialbuild.py" no further setup will be required, and the "articlesearch.py" will be ready to be run on the host machine.

More likely than not, you have not used this, customized your settings, or are running the script on a separate machine than the one the DB is on. In that case, you will have to customize the default options in the "connect" function in the "articlesearch.py" file.

## Postgres Setup
A [postgres](https://www.postgresql.org/) DB is required. At the very basic level, you have to have it installed. For customized setups, settings have to be adjusted in the "initalbuild.py" file and the "articlesearch.py" file. 

## Usage
All needed functions after the first setup are in the "articlesearch.py" file. They are all async functions and thus need to be run in an async loop. (A basic example can be seen in "autoinitalbuild.py" using asyncio.)

#### Update
Looks for and adds new articles to the database.

#### Search
Searches the database for a given input.\
Takes string as input. Example: "--title --limit=5 words and more words"\
Options:\
--title: Searches only in the titles of the articles (default search mode)\
--content: Searches only in the content of an article, and ignores the title\
--searchall: Searches both title and content of an article\
--searchreverse: Searches the DB from the oldest article\
--limit: Returns only the latest results up to number given (default 5). Format: limit=XYZ\
--limitall: Returns all results found\
--before: Looks for articles that were written before a given date. Format: YYYY-MM-DD\
--after: Looks for articles that were written after a given date. Format: YYYY-MM-DD\
If both the --after & --before tags are given, the search is limited to the dates between both options.

#### Read
Returns the record for the article with the given ID.\
Takes string as input. Example: Passing "1" as input would return the record with ID number 1 from the database

#### Count
Counts the amount of articles that fit the given conditions.\
Takes string as input. Example: "--content --before=3305-06-23"\
Options:\
--title: Counts the amount of articles that contain a certain term in the title.\
--content: Counts the amount of articles that contain a certain term only in their content.\
--all: Counts the amount of articles that contain a certain term in either the title or the content.\
--before: Counts the amount of articles before a given date. Format: YYYY-MM-DD\
--after: Counts the amount of articles after a given date. Format: YYYY-MM-DD\
If both the --after & --before tags are given, the search is limited to the dates between both options.

## Contact
To get help, report an issue, or propose an idea, head to the [issues section](https://github.com/Scaleios/Galnet-Newsfeed/issues) on the [github page](https://github.com/Scaleios/Galnet-Newsfeed/).