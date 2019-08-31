#! /usr/bin/env python

import jinja2
import htmlmin

import enricher


class HTMLFormatter(object):

    def __init__(self, fake=False):
        self.fake = fake
        self.jinja_environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader("."))
        self.general_template = self.jinja_environment.get_template(
            "general_report_template.html")
        self.user_template = self.jinja_environment.get_template(
            "user_report_template.html")
        self.enricher = enricher.Enricher(fake=fake)

    def user_format(self, report, uid):
        self.enricher.user_enrich(report, uid)
        user_stats = report['user_stats'][uid]
        html_report = self.user_template.render(
            payload=report, user_stats=user_stats, uid=uid)
        minified_html_report = htmlmin.minify(html_report,
                                              remove_comments=True,
                                              remove_empty_space=True,
                                              remove_all_empty_space=True,
                                              reduce_boolean_attributes=True
                                              )
        return minified_html_report

    def format(self, report):
        self.enricher.enrich(report)
        html_report = self.general_template.render(
            payload=report, statistics=report['statistics'])
        minified_html_report = htmlmin.minify(html_report,
                                              remove_comments=True,
                                              remove_empty_space=True,
                                              remove_all_empty_space=True,
                                              reduce_boolean_attributes=True
                                              )
        return minified_html_report
