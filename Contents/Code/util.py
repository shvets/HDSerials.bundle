# -*- coding: utf-8 -*-

def get_language():
    return Prefs['language'].split('/')[1]

def validate_prefs():
    language = get_language()

    if Core.storage.file_exists(Core.storage.abs_path(
        Core.storage.join_path(Core.bundle_path, 'Contents', 'Strings', '%s.json' % language)
    )):
        Locale.DefaultLocale = language
    else:
        Locale.DefaultLocale = 'en-us'

def no_contents(name=None):
    if not name:
        name = 'Error'

    return ObjectContainer(header=unicode(L(name)), message=unicode(L('No entries found')))

