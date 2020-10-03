 # Changes and Updates
 Documenting all the updates and changes the program receives on numbered version.
 
 
 ## 1.0
 Initial release of program.
 
 Future note: search needs to be improved.
  
  
 ## 1.1
 - Added the ability to customize bot settings from JSON file
 - Added check to prevent articles with duplicate IDs from being added twice
 
 Notes to people upgrading to this version:
 - To update your database, and perform
   some general cleanup, be sure to run `python/update_to_1.1.py`.
 - Be prepared for errors to happen. Back up your database before running,
   to avoid a rebuild.
 - Settings files have been modified, and will be modified for every version.
   Be sure to back up your settings, and update them.
 - A new settings file has been added to the discord bot (`BotSettings.json`).
   Be sure to fill it in.
