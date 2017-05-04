croissant 🥐
============
Croissant is a very simple static-file blogging engine, using markdown files as input.

***DISCLAIMER***  
*Croissant should be treated as an early alpha. You should also probably not use it.*

Croissant is something I've wanted to create for a long time, but never really sat down to do it. I decided to try to make it in a week and see what happens. The resulting code is not something I'm proud of, and there are definitely *much* better static blogging engines out there, but I decided to upload it anyway and hope for some feedback!

I know the name isn't original (github returns another 100 entries for `croissant` and at least one of them is a blogging engine). A package named croissant already exists at PyPI, too. But that's the name I came up with when thinking about creating a [baked blog](http://inessential.com/2011/03/16/a_plea_for_baked_weblogs) engine and ultimately I decided that I liked the name enough --or cared too little to come up with something more original, you decide-- to keep it.

Installation
------------
Croissant requires Python 3.

	pip3 install regex Markdown PyYAML Unidecode Jinja2
	git clone https://github.com/ftsagkris/croissant.git
	cd croissant
	Edit config/config.yaml
	python3 croissant.py

Every time you run it, croissant checks for updates in the posts, pages and media subdirectories under its source directory. If any changes are detected, croissant will only render what's changed and output the rendered files at the specified output. You can run it either locally and copy the files to your server's webroot, or directly on the server.

I run it directly on a VPS and use a Dropbox folder as the source directory. This way you can add or edit files from anywhere.

You can schedule a cron job to run the script every minute like this:

	* * * * * python3 /path/to/croissant/croissant.py

or, even better, use `inotifywait` to respond to file changes, as they happen.

Basics
------
####Post structure:

	Post title underlined by three or more equals signs
	===================================================
	date: 2017-05-04
	slug: my-title
	link: http://link.to/post
	draft: false
	
	Post's main body.
	
	There should be at least one empty line between the 
	post's frontmatter and body.

All meta tags are optional. If you don't provide a custom slug, croissant will make a slug out of your post's title. If you don't provide a date, croissant will use the current date. The other two tags have a default value of `False`.

**Static page structure:**

	About me
	========
	slug: about
	
	I'm a blogger!

Again, `slug` is optional.

**Source folder structure:**

	<specified-src-folder>/
		posts/
			my-first-post.md
			another-post.md
			...
		
		pages/
			about.md
			contact.md
			...
		
		media/
			screenshot.png
			...

***IMPORTANT***  
If you delete a post/page/file from your source folder, the next time croissant runs, it will remove it from your blog. This is not a bug. It's the only good way to be able to delete files while on the go, since croissant is really designed to use a Dropbox folder as its source.

Croissant will output a very basic archive of all your posts under `http://specified-url.com/archive` and an RSS feed under `http://specified-url.com/rss.xml`.

Drafts
------
You may notice that in the `config.yaml` file there is a `public drafts` option. If you set it to `True`, croissant will output your drafts under `http://specified-url.com/drafts/post-slug`. You may not want that. I do, so that I can quickly preview a post before it is rendered in the blog's homepage and RSS feed.

If you set it to `False`, croissant will create a `drafts` folder under your source folder and output a preview of your draft there.