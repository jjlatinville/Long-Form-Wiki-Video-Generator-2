#!/bin/bash
# rename_module.sh - Create consistent module names by copying files

# Check if title-cards.py exists (hyphenated)
if [ -f "title-cards.py" ] && [ ! -f "title_cards.py" ]; then
    echo "Creating title_cards.py from title-cards.py"
    cp "title-cards.py" "title_cards.py"
fi

# Check if any other module files need fixing
if [ -f "wiki-grabber.py" ] && [ ! -f "wiki_grabber.py" ]; then
    echo "Creating wiki_grabber.py from wiki-grabber.py"
    cp "wiki-grabber.py" "wiki_grabber.py"
fi

echo "Module files are now ready for import"
