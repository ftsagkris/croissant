#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from shutil import copyfile
import glob
import time
from datetime import datetime
from collections import OrderedDict

import re
import markdown
import yaml
import unidecode
from jinja2 import Environment, FileSystemLoader


def slugify(text):
    # credit: http://stackoverflow.com/a/8366771
    text = unidecode.unidecode(text.strip()).lower()
    return re.sub(r'\W+', '-', text)


class Croissant:

    def __init__(self, root):
        config_path = os.path.join(root, 'config/')
        self.templates_path = os.path.join(root, 'templates/')
        self.posts = {}
        self.rendered_posts = os.path.join(config_path, 'rendered_posts.yaml')
        self.pages = {}
        self.rendered_pages = os.path.join(config_path, 'rendered_pages.yaml')
        self.media = {}
        self.moved_media = os.path.join(config_path, 'moved_media.yaml')
        config = self.load_config(config_path)

        blog = config['blog']
        if not blog['url'].endswith('/'):
            blog['url'] += '/'

        self.blog_url = blog['url']
        self.posts_in_homepage = config['posts_in_homepage']
        self.rss_posts = 20
        self.source_path = config['source_path']
        self.posts_path = os.path.join(self.source_path, 'posts/')
        self.pages_path = os.path.join(self.source_path, 'pages/')
        self.media_path = os.path.join(self.source_path, 'media/')

        self.webroot = config['webroot']
        self.public_drafts = config['public_drafts']
        if self.public_drafts:
            self.drafts_output = os.path.join(self.webroot, 'drafts/')
        else:
            self.drafts_output = os.path.join(self.source_path, 'drafts/')

        self.chk_dirs()

        self.env = Environment(loader=FileSystemLoader(self.templates_path))
        self.env.globals['blog'] = blog

        self.updated_posts = False

    def chk_dirs(self):
        if not os.path.isdir(self.source_path):
            print('Warning: Source path not found at: ', self.source_path)
            print('Creating source path')
            os.makedirs(self.source_path)
        if not os.path.isdir(self.posts_path):
            os.mkdir(self.posts_path)
        if not os.path.isdir(self.pages_path):
            os.mkdir(self.pages_path)
        if not os.path.isdir(self.media_path):
            os.mkdir(self.media_path)

        if not os.path.isdir(self.webroot):
            print('Warning: Webroot not found at: ', self.webroot)
            print('Creating webroot')
            os.makedirs(self.webroot)

    def store_rendered_files(self, destination, dictionary):
        with open(destination, 'w') as yaml_file:
            yaml.dump(dictionary, yaml_file, default_flow_style=False)

    def load_config(self, config_path):
        try:
            with open(self.rendered_posts, 'r') as posts_dict:
                self.posts = yaml.load(posts_dict)

                """ Creating new dict if YAML file is empty to prevent self.posts
                from becoming 'NoneType' object
                """
                if not self.posts:
                    self.posts = {}
        except IOError as error:
            print(error)
            print('Creating new rendered posts YAML file.')
            f = open(self.rendered_posts, 'w')
            f.close()

        try:
            with open(self.rendered_pages, 'r') as pages_dict:
                self.pages = yaml.load(pages_dict)

                if not self.pages:
                    self.pages = {}
        except IOError as error:
            print(error)
            print('Creating new rendered pages YAML file.')
            f = open(self.rendered_pages, 'w')
            f.close()

        try:
            with open(self.moved_media, 'r') as media_dict:
                self.media = yaml.load(media_dict)

                if not self.media:
                    self.media = {}
        except IOError as error:
            print(error)
            print('Creating new moved media YAML file.')
            f = open(self.moved_media, 'w')
            f.close()

        try:
            with open(os.path.join(config_path, 'config.yaml'), 'r') as config:
                config = yaml.load(config)
        except IOError as error:
            print(error)
            sys.exit('Please provide configuration file')
        else:
            return config

    def update(self):
        self.check_for_updated_posts()
        self.check_for_updated_pages()
        self.check_for_updated_media()

        home_exists = os.path.isfile(os.path.join(self.webroot, 'index.html'))
        rss_exists = os.path.isfile(os.path.join(self.webroot, 'rss.xml'))
        archive_exists = os.path.isfile(os.path.join(self.webroot, 'archive/', 'index.html'))

        if self.updated_posts or not home_exists:
            self.render_homepage()
        if self.updated_posts or not rss_exists:
            self.render_rss()
        if self.updated_posts or not archive_exists:
            self.render_archive()

    def check_for_updated_posts(self):
        for post in os.listdir(self.posts_path):
            ext = os.path.splitext(post)[-1].lower()
            if ext == '.md' or ext == '.markdown' or ext == '.txt':
                if post not in self.posts:
                    print('New post found:', post)
                    self.add_post(post, new=True)
                elif not self.is_post_rendered(post) and not self.posts[post]['draft']:
                    print('Post \'%s\' has been previously rendered but was '\
                          'not found in site directory' % post)
                    self.add_post(post)
                else:
                    post_updated = self.posts[post]['mod'] \
                        < os.path.getmtime(os.path.join(self.posts_path, post))
                    if post_updated:
                        print('Post to update:', post)
                        self.add_post(post)

        for post in list(self.posts.keys()):
            if not os.path.isfile(os.path.join(self.posts_path, post)):
                print('Deleting post:', post)
                self.remove_post(post)
                self.updated_posts = True
                del self.posts[post]
                print('Done')

        self.store_rendered_files(self.rendered_posts, self.posts)

    def check_for_updated_pages(self):
        for page in os.listdir(self.pages_path):
            ext = os.path.splitext(page)[-1].lower()
            if ext == '.md' or ext == '.markdown' or ext == '.txt':
                if page not in self.pages:
                    print('New page found:', page)
                    self.add_page(page, new=True)
                elif not self.is_page_rendered(page):
                    print('Page \'%s\' has been previously rendered but was ' \
                          'not found in site directory' % page)
                    self.add_page(page)
                else:
                    page_updated = self.pages[page]['mod'] \
                        < os.path.getmtime(os.path.join(self.pages_path, page))
                    if page_updated:
                        print('Page to update:', page)
                        self.add_page(page)

        for page in list(self.pages.keys()):
            if not os.path.isfile(os.path.join(self.pages_path, page)):
                print('Deleting page:', page)
                self.remove_page(page)
                del self.pages[page]
                print('Done')

        self.store_rendered_files(self.rendered_pages, self.pages)

    def check_for_updated_media(self):
        for data_file in os.listdir(self.media_path):
            # This is for macOS
            if data_file != '.DS_Store':
                if data_file not in self.media:
                    print('New file found: ', data_file)
                    self.add_file(data_file)
                elif not self.is_file_moved(data_file):
                    print('File \'%s\' has been previously moved but was not found' \
                          ' in site directory' % data_file)
                    self.add_file(data_file)
                else:
                    file_updated = self.media[data_file]['mod'] \
                        < os.path.getmtime(os.path.join(self.media_path, data_file))
                    if file_updated:
                        print('File to update: ', data_file)
                        self.add_file(data_file)

        for data_file in list(self.media.keys()):
            if not os.path.isfile(os.path.join(self.media_path, data_file)):
                print('Deleting file: ', data_file)
                self.remove_file(data_file)
                del self.media[data_file]
                print('Done')

        self.store_rendered_files(self.moved_media, self.media)

    def add_post(self, post, new=False):
        self.updated_posts = True
        mod_time = os.path.getmtime(os.path.join(self.posts_path, post))
        try:
            with open(os.path.join(self.posts_path, post), 'r') as source:
                txt = source.read()
                try:
                    (meta, body) = re.split('\n{2,}', txt, 1)
                    (title, meta) = re.split('={3,}', meta, 1)
                except ValueError as error:
                    print(error)
                else:
                    if yaml.load(meta):
                        meta = yaml.load(meta)
                    else:
                        meta = {}
                    meta = self.set_post_meta(meta, title, post, new)

                    if not new:
                        if self.posts[post]['slug'] != meta['slug']:
                            post_path = self.is_post_rendered(post)
                            if post_path:
                                parent_path = os.path.split(os.path.dirname(post_path))[0]
                                new_path = os.path.join(parent_path, meta['slug'])
                                os.rename(post_path, new_path)

                        if self.posts[post]['published'] != meta['date']:
                            self.remove_post(post)

                        if self.posts[post]['draft'] != meta['draft']:
                            if meta['draft']:
                                self.remove_post(post)
                            else:
                                self.remove_draft(post)

                    self.posts[post] = {
                        'mod': int(mod_time),
                        'published': meta['date'],
                        'title': meta['title'],
                        'slug': meta['slug'],
                        'link': meta['link'],
                        'draft': meta['draft']
                    }

                    self.render_post(meta, body)

                    print('Rendered:', post)
        except IOError as error:
            print(error)

    def add_page(self, page, new=False):
        mod_time = os.path.getmtime(os.path.join(self.pages_path, page))
        try:
            with open(os.path.join(self.pages_path, page), 'r') as source:
                txt = source.read()
                try:
                    (meta, body) = re.split('\n{2,}', txt, 1)
                    (title, meta) = re.split('={3,}', meta, 1)
                except ValueError as error:
                    print(error)
                else:
                    if yaml.load(meta):
                        meta = yaml.load(meta)
                    else:
                        meta = {}
                    meta = self.get_page_meta(meta, title)

                    if not new:
                        if self.pages[page]['slug'] != meta['slug']:
                            page_path = self.is_page_rendered(page)
                            if page_path:
                                new_path = os.path.join(self.webroot, meta['slug'])
                                os.rename(page_path, new_path)

                    self.pages[page] = {
                        'mod': int(mod_time),
                        'title': meta['title'],
                        'slug': meta['slug']
                    }

                    self.render_page(meta, body)

                    print('Rendered page:', page)
        except IOError as error:
            print(error)

    def add_file(self, data_file):
        mod_time = os.path.getmtime(os.path.join(self.media_path, data_file))
        src = os.path.join(self.media_path, data_file)
        if os.path.isfile(src):
            dst = os.path.join(self.webroot, 'media/', data_file)
            copyfile(src, dst)
            self.media[data_file] = {
                'mod': int(mod_time)
            }
            print('Moved file: ', data_file)

    def remove_post(self, post):
        post_path = self.is_post_rendered(post)
        if post_path:
            post_index = os.path.join(post_path, 'index.html')
            try:
                os.remove(post_index)
                os.rmdir(post_path)
                month_path = os.path.dirname(post_path)
                # This is one of those times, when I hate macOS
                if not len([name for name in os.listdir(month_path) \
                            if name != ".DS_Store"]):
                    if os.path.isfile(os.path.join(month_path, '.DS_Store')):
                        os.remove(os.path.join(month_path, '.DS_Store'))
                    os.rmdir(month_path)
                    year_path = os.path.dirname(month_path)
                    if not len([name for name in os.listdir(year_path) \
                                if name != ".DS_Store"]):
                        if os.path.isfile(os.path.join(year_path, '.DS_Store')):
                            os.remove(os.path.join(year_path, '.DS_Store'))
                        os.rmdir(year_path)
            except OSError as error:
                print(error)

    def remove_draft(self, post):
        post_path = os.path.join(self.drafts_output, self.posts[post]['slug'])
        if os.path.isdir(post_path):
            post_index = os.path.join(post_path, 'index.html')
            try:
                os.remove(post_index)
                os.rmdir(post_path)
            except OSError as error:
                print(error)

    def remove_page(self, page):
        page_path = self.is_page_rendered(page)
        if page_path:
            page_index = os.path.join(page_path, 'index.html')
            try:
                os.remove(page_index)
                os.rmdir(page_path)
            except OSError as error:
                print(error)

    def remove_file(self, data_file):
        file_path = self.is_file_moved(data_file)
        if file_path:
            try:
                os.remove(file_path)
            except OSError as error:
                print(error)

    def set_post_meta(self, meta, title, post, new):
        meta['title'] = title.strip()
        if 'date' in meta:
            meta['date'] = datetime.strptime(str(meta['date']).strip(), '%Y-%m-%d')
        else:
            if new:
                """ If a new post doesn't provide a publish date in its
                metadata, croissant uses initial submission time as the
                post's publish date. This only happens when a post is
                initially submitted so that way if you update a post,
                publish date doesn't change.
                """
                meta['date'] = datetime.fromtimestamp(time.time())
            else:
                meta['date'] = self.posts[post]['published']
        if 'link' not in meta:
            meta['link'] = False
        if 'slug' not in meta:
            meta['slug'] = slugify(title)
        if 'draft' not in meta:
            meta['draft'] = False
        return meta

    def get_page_meta(self, meta, title):
        meta['title'] = title.strip()
        if 'slug' not in meta:
            meta['slug'] = slugify(title)
        return meta

    def render_post(self, meta, body):
        html_body = markdown.markdown(body, output_format='html5')
        html_body = self.rewrite_links(html_body)

        if not meta['draft']:
            post_path = '%s/%s/%s' % (
                str(meta['date'].year),
                str('{:02d}'.format(meta['date'].month)),
                meta['slug'])
            meta['uri'] = post_path
        else:
            post_path = os.path.join(self.drafts_output, meta['slug'])

        template = self.env.get_template('post.html')
        if not os.path.isdir(os.path.join(self.webroot, post_path)):
            os.makedirs(os.path.join(self.webroot, post_path))
        post_html = open(os.path.join(self.webroot, post_path, 'index.html'), 'w')
        post_html.write(template.render(meta=meta, body=html_body))
        post_html.close()

    def render_page(self, meta, body):
        html_body = markdown.markdown(body, output_format='html5')
        html_body = self.rewrite_links(html_body)

        page_path = meta['slug']

        template = self.env.get_template('page.html')
        if not os.path.isdir(os.path.join(self.webroot, page_path)):
            os.makedirs(os.path.join(self.webroot, page_path))
        page_html = open(os.path.join(self.webroot, page_path, 'index.html'), 'w')
        page_html.write(template.render(meta=meta, body=html_body))
        page_html.close()

    def render_homepage(self):
        # Getting non-draft posts
        published_posts = dict(post for post in self.posts.items() if not post[1]['draft'])
        # Ordering posts by publish date
        ordered_posts = OrderedDict(sorted(published_posts.items(),
                                           key=lambda t: t[1]['published'], reverse=True))
        # Keeping specified newest posts
        newest_posts = list(ordered_posts)[:self.posts_in_homepage]

        homepage_posts = {}
        for post in newest_posts:
            title = self.posts[post]['title']
            date = self.posts[post]['published']
            with open(os.path.join(self.posts_path, post), 'r') as source:
                txt = source.read()
                try:
                    (_, body) = re.split('\n{2,}', txt, 1)
                except ValueError as error:
                    print(error)
                else:
                    html_body = markdown.markdown(body, output_format='html5')
                    html_body = self.rewrite_links(html_body)
            uri = '/%s/%s/%s' % (
                date.year,
                str('{:02d}'.format(date.month)),
                self.posts[post]['slug']
            )
            link = self.posts[post]['link']
            homepage_posts[post] = {
                'title': title,
                'date': date,
                'body': html_body,
                'uri': uri,
                'link': link
            }
        
        # Reordering posts
        ordered_posts = OrderedDict(sorted(homepage_posts.items(),
                                           key=lambda t: t[1]['date'], reverse=True))

        template = self.env.get_template('home.html')
        home_html = open(os.path.join(self.webroot, 'index.html'), 'w')
        home_html.write(template.render(posts=ordered_posts.items()))
        home_html.close()
        print('Rendered homepage')

    def render_archive(self):
        # Getting non-draft posts
        published_posts = list(dict(post for post in self.posts.items() if not post[1]['draft']))

        archive_posts = {}
        for post in published_posts:
            title = self.posts[post]['title']
            date = self.posts[post]['published']
            uri = '/%s/%s/%s' % (
                date.year,
                str('{:02d}'.format(date.month)),
                self.posts[post]['slug']
            )
            archive_posts[post] = {
                'title': title,
                'date': date,
                'uri': uri,
            }

        ordered_posts = OrderedDict(sorted(archive_posts.items(),
                                           key=lambda t: t[1]['date'], reverse=True))

        template = self.env.get_template('archive.html')
        if not os.path.isdir(os.path.join(self.webroot, 'archive/')):
            os.makedirs(os.path.join(self.webroot, 'archive/'))
        archive_html = open(os.path.join(self.webroot, 'archive/', 'index.html'), 'w')
        archive_html.write(template.render(posts=ordered_posts.items()))
        archive_html.close()
        print('Rendered archive page')

    def render_rss(self):
        # Getting non-draft posts
        published_posts = dict(post for post in self.posts.items() if not post[1]['draft'])
        # Ordering posts by publish date
        ordered_posts = OrderedDict(sorted(published_posts.items(),
                                           key=lambda t: t[1]['published'], reverse=True))
        # Keeping specified newest posts
        newest_posts = list(ordered_posts)[:self.rss_posts]

        rss_posts = {}
        for post in newest_posts:
            title = self.posts[post]['title']
            date = self.posts[post]['published']
            with open(os.path.join(self.posts_path, post), 'r') as source:
                txt = source.read()
                try:
                    (_, body) = re.split('\n{2,}', txt, 1)
                except ValueError as error:
                    print(error)
                else:
                    html_body = markdown.markdown(body, output_format='html5')
                    html_body = self.rewrite_links(html_body)
            url = '%s%s/%s/%s' % (
                self.blog_url,
                date.year,
                str('{:02d}'.format(date.month)),
                self.posts[post]['slug']
            )
            link = self.posts[post]['link']
            rss_posts[post] = {
                'title': title,
                'date': date,
                'body': html_body,
                'url': url,
                'link': link
            }

        # Reordering posts
        ordered_posts = OrderedDict(sorted(rss_posts.items(),
                                           key=lambda t: t[1]['date'], reverse=True))

        template = self.env.get_template('rss.xml')
        rss_html = open(os.path.join(self.webroot, 'rss.xml'), 'w')
        rss_html.write(template.render(posts=ordered_posts.items()))
        rss_html.close()
        print('Rendered RSS feed')

    def is_post_rendered(self, post):
        post_date = self.posts[post]['published']
        post_path = '%s/%s/%s' % (
            str(post_date.year),
            str('{:02d}'.format(post_date.month)),
            self.posts[post]['slug']
        )

        if os.path.isdir(os.path.join(self.webroot, post_path)):
            return os.path.join(self.webroot, post_path)
        else:
            return False

    def is_page_rendered(self, page):
        if os.path.isdir(os.path.join(self.webroot, self.pages[page]['slug'])):
            return os.path.join(self.webroot, self.pages[page]['slug'])
        else:
            return False

    def is_file_moved(self, data_file):
        if os.path.isfile(os.path.join(self.webroot, 'media/', data_file)):
            return os.path.join(self.webroot, 'media/', data_file)
        else:
            return False

    def rewrite_links(self, text):
        text = re.sub(
            r" src=[\"'](../media/)([^/]+?)[\"']",
            ' src="%s%s/%s"' % (self.blog_url, 'media', r"\2"),
            text
        )
        text = re.sub(
            r" href=[\"'](../media/)([^/]+?)[\"']",
            ' href=%s/%s/%s' % (self.blog_url, 'media', r"\2"),
            text
        )

        return text

if __name__ == '__main__':
    start_time = time.time()
    
    # credit: http://stackoverflow.com/a/789383
    pid = str(os.getpid())
    pidfile = '/tmp/croissant-daemon.pid'

    if os.path.isfile(pidfile):
        sys.exit('%s already exists, exiting' % pidfile)
    with open(pidfile, 'w') as f:
        f.write(pid)
        try:
            cur_path = sys.path[0]
            croissant = Croissant(cur_path)
            croissant.update()
        finally:
            os.unlink(pidfile)
    elapsed_time = time.time() - start_time
    print("%.2f seconds" % elapsed_time)