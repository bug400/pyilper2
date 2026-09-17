#!/bin/bash
#
# Script to generate the online HTML documentation
if [ "`dirname $0`" != "." ] ; then
   echo "script must be called from its subdirectory"
   exit 1
fi
rm ../Manual/*.html
rm -rf ../Manual/css
for i in *.html; do cat tools/header.html $i tools/footer.html > ../Manual/$i
cp -r css ../Manual
done
