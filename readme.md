## PyTMX - Python 3+2


This experimental branch is a testbed for new features for the version that will
work cleanly on python2 and 3 with no changes to the source code.

Working!

#### See the "apps" folder for example use!  (used to be "test")

## Key Differences

I've tweaked many small things for a cleaner, more 'pythonic' library.

- Better pep8 compliance
- More use of iterators
- More functions to find layers

#### Objects have all property metadata stored in "properties" attribute.
This means no more object.__dict__ hacks.  I really didn't think that through
before.  Now you can just access properties like this:
>>> object.properties['key']
"value"

...and finally...

# New method names  D:

To have pep8 compatibility, I've made the choice to change the method names from
CamelCase to under_score.  Fortunately, it is just a cosmetic change.

If you have used pytmx for python2 and you are starting a new project in python
3.x, then you can simply use the new 'six' branch.

Don't worry, I will still continue to support the older code, although, it may
not get any cool new features.

### Have Fun!