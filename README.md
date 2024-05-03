# BETTER CALENDAR

## Disclaimer

Unfortunately, without disclosing confidential information, it would be difficult to allow someone else to run this application on their local machine, because running this app requires knowing secret keys to run the server, that interacts with the Google API. These special credentials are known to both the application and Google and they are used for authentification of the server, they allow connectoin to Google API services and they allow the app to request consent of a user to access their data (source: https://stackoverflow.com/questions/72171227/what-does-the-google-client-secret-in-an-oauth2-application-give-access-to#:~:text=Client%20id%20and%20client%20secret,tokens%20from%20your%20refresh%20tokens.). If someone else had this information, they could access the same Google API services that Better Calendar uses. This is why a part of the code at the top of `app.py` is missing and the app can't be run on someone else's local machine.


## The idea of Better Calendar

Better Calendar is a web application that extends the functionality of standart Google Calendar using Flask and Google Calendar API. Better Calendar gathers statistical information about the user's time investments in varoius things based on their planned events in Google Calendar, after the user logs in via. Better Calendar then processes this information and gives it to the user in the form of multiple bar charts, that represent how many hours the user planned for their activities on certain calendars in Google Calendar this year, previous month, this month and this week. For example, using Better Calendar, one could easily find out how many hours did their planned events take for a calendar called "Study" or a calendar called "Church".


## Project structure

`app.py` is the main file of the flask application. It contains all of the fuctionality regarding routing, logging in via oauth, collecting data from Google Calendar API. The `/templates` folder contains four html templates. One of them is a layout that is used on every page with the use of Jinja, and the other three are html pages of the application. The static folder contains a static logo and a css styles file.


Parts of the application and "user flow"

When the user first opens the app, the first page they will see is the welcome page. It is displayed when someone, who is not logged in opens the application at the root url. On this page, the user can log into the application with their Google account by clicking the link that will redirect them to `/login` url. There, the process of logging in with Google Oauth begins with the help of authlib library for python.

After the user has given their consent and authenticated with Google, after a series of back and forth requests between the application and Google API (explained here: https://developers.google.com/identity/protocols/oauth2) the user is redirected to `/callback` URL, where the acces token, needed to make authorized requests to the API. The user data is stored in session, provided by Flask.

Then, the user is redirected to the main page of the application: `/hours`. There, the app makes a series of requests to the Google Calendar API, fetching the data about the events that user has planned in their calendars. This is done inside a function `get_all_events(token)`. Via the use of dateutils library, the app accounts for timezones. Then, in `hours()` the app counts the sum of hours of the events for 4 different time intervals: this year up to the end of current week, previous month, this month up to the end of current week and the current week. Some JavaScript code in `/templates/hours.html` via barchart.js library visualises this data in barcharts, that are split into four tabs for each time interval using Bootstrap.

If the user's accsess token ever runs out, they will be shown the `/templates/renew_login.html` page, where they would be able to log in again.


## A note on colors

Colors of the barchart bars on the `/hours` page match the chosen colors of the corresponding calendars, which these bars represent. There are two possible ways a color of a calendar could be rendered. The first way is if the user selects a custom color for their calendar. Then, there is no issue: the API stores the colors of the calendars that we can fetch and then use. The other way is if the user selects one of Google Calendar's default colors. Therein lies the catch: when using Google Calendar, you can choose between two color palettes, called "modern" and "classic". These color palettes change the default colors and the default color of the calendar is stored with the calendar object. BUT! In the API they only store the "classic" RGB value, there is no "modern" color value, and the ID of the color stays the same regardless of whether or not the user switches to "modern" color palette. It seems like the change to "modern" colors happens on the client and not on the server. So, Better Calendar had to do the same thing: in the top right corner of the `/hours` page there is a settings button, that lets the user switch between these color palettes. It is achieved by storing modern colors as a dictionary, where key is the id of the color, that is the same regardless of the chosen color palette, and the value is the corresponding modern color. This way, by knowing the Id of the color of a calendar, we get both "modern" and "classic" color values. The app also lets the user to choose a default color palette, that is saved stored in session so that the user doesn't have to change his preferred color palette every time they open the app.
