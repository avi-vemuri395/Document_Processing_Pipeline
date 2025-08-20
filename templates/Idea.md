/plan-or-debug is running… ok now - im questioning the whole fuction model to this. we
 will have more to the degree of 2-4 applications a month, max.

we also dont plan to grow past these 3 partner banks.

A while back, we ideated on schema driven extractoin.

look at this openai doc and index it with nia:
https://platform.openai.com/docs/guides/structured-outputs

think about this and evaluate my approach / thoughts below:

since we only have 9 template forms to fill out at most, why cant we run those through
the google document parser, then sanitize it very well, and we can even manually
manipulate it because we know each template wont change for the forseeable future.

So, when a user has uploaded all their data and its successfully saved into this
master.json file, why cant we just use the open ai model to extract the schema for each
form (because we will already have a forms json extracted template), and then populate
the pdf with the extracted data?

we will be calling the llm for each form but that is a small price to pay since our
margins are very good on profit, and we are currnely not worried about massive scale -
rather we want a decently accurate workign solution and its okay to have some manual
intervention.

think deeply about this and let me know what you think of my approach.
