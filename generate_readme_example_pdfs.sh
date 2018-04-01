cd src
python3 scroll.py 753,751 letter ../example_1.pdf
python3 scroll.py 762 letter ../example_2.pdf --recursive
python3 scroll.py 753,751 letter ../example_3.pdf --meeting-font=dejavuserif
python3 scroll.py 762 letter ../example_4.pdf \
    --recursive \
    --main-header-field=weekday \
    --second-header-field=city \
    --meeting-font-size=7 \
    --header-font-size=7 \
    --time-column-width=12 \
    --duration-column-width=10
python3 scroll.py 762 letter ../example_5.pdf \
    --recursive \
    --bookletize \
    --main-header-field=weekday \
    --second-header-field=city \
    --meeting-font-size=7 \
    --header-font-size=7 \
    --time-column-width=12 \
    --duration-column-width=10
cd ..
