from enso.contrib.open import interfaces

URLS = [
    "http://www.microsoft.com", "https://www.google.cz/search?q=python+ABCMeta&ie=utf-8&oe=utf-8&gws_rd=cr&ei=GFhSVoL4FIWKU8D9kagF"
]

NON_URLS = [
    # this could be as well valid filename
    "file", "file.txt", "file/path/dir", "../file/path/dir", "./file/path/dir", "/file/path/dir", "~/.bash_profile", "c:\\test\\path\\file.txt", "www.something.com"
]


def test_is_url():
    for url in URLS:
        assert interfaces.is_valid_url(url)
    for non_url in NON_URLS:
        assert not interfaces.is_valid_url(non_url)


def test_is_url2():
    for url in URLS:
        assert interfaces.is_url2(url)
    for non_url in NON_URLS:
        assert not interfaces.is_url2(non_url)


if __name__ == '__main__':
    pass
