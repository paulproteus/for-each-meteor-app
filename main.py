if __name__ == '__main__':
    import ok
    import sys
    if sys.argv[1:]:
        url_generator_callable = lambda: iter(sys.argv[1:])
    else:
        url_generator_callable = None
    ok.main(url_generator_callable=url_generator_callable)
