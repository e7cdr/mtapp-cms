Streams app

This might be one of the most important part of the CMS. It is in charge of creating all the blocks used in every page.
Basically, you create an html component (like cards.html), create the StreamBlock in blocks.py and then call these blocks wherever
you wish. If you would like to use cards block in, for example, the home page, you can go to the Home app model and import this
cards block into the model as a StreamField. This makes all the blocks REUSABLE!

The blocks are created as StructBlocks in blocks.py and then imported inside a StreamField (or StreamBlock depending on the use case)