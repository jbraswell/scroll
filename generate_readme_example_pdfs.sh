cd src
mkdir -p ../examples/
python3 scroll.py 753,751 letter ../examples/example_1.pdf
python3 scroll.py 762 letter ../examples/example_2.pdf --recursive
python3 scroll.py 753,751 letter ../examples/example_3.pdf --meeting-font=dejavuserif
python3 scroll.py 762 letter ../examples/example_4.pdf \
    --recursive \
    --main-header-field=weekday \
    --second-header-field=city \
    --meeting-font-size=8 \
    --header-font-size=8 \
    --time-column-width=15 \
    --duration-column-width=10
python3 scroll.py 762 letter ../examples/example_5.pdf \
    --recursive \
    --bookletize \
    --main-header-field=weekday \
    --second-header-field=city \
    --meeting-font-size=8 \
    --header-font-size=8 \
    --time-column-width=15 \
    --duration-column-width=10
cd ..
aws s3 sync --profile personal --acl public-read examples s3://scroll-examples/
