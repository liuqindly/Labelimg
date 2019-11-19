LabelImg

Installation
------------------

Download prebuilt binaries
~~~~~~~~~~~~~~~~~~~~~~~~~~

-  `Windows & Linux <https://tzutalin.github.io/labelImg/>`__

-  macOS. Binaries for macOS are not yet available. Help would be appreciated. At present, it must be `built from source <#macos>`__.

Build from source
~~~~~~~~~~~~~~~~~

Linux/Ubuntu/Mac requires at least `Python
2.6 <https://www.python.org/getit/>`__ and has been tested with `PyQt
4.8 <https://www.riverbankcomputing.com/software/pyqt/intro>`__.


Ubuntu Linux
^^^^^^^^^^^^
Python 2 + Qt4

.. code::

    sudo apt-get install pyqt4-dev-tools
    sudo pip install lxml
    make qt4py2
    python labelImg.py
    python labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

Python 3 + Qt5

.. code::

    sudo apt-get install pyqt5-dev-tools
    sudo pip3 install lxml
    make qt5py3
    python3 labelImg.py
    python3 labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

macOS
^^^^
Python 2 + Qt4

.. code::

    brew install qt qt4
    brew install libxml2
    make qt4py2
    python labelImg.py
    python  labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

Python 3 + Qt5 (Works on macOS High Sierra)

.. code::

    brew install qt  # will install qt-5.x.x
    brew install libxml2
    make qt5py3
    python labelImg.py
    python  labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]


Windows
^^^^^^^

Download and setup `Python 2.6 or
later <https://www.python.org/downloads/windows/>`__,
`PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`__
and `install lxml <http://lxml.de/installation.html>`__.

Open cmd and go to `labelImg <#labelimg>`__ directory

.. code::

    pyrcc4 -o resources.py resources.qrc
    python labelImg.py
    python labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

Get from PyPI
~~~~~~~~~~~~~~~~~
.. code::

    pip install labelImg
    labelImg
    labelImg [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

I tested pip on Ubuntu 14.04 and 16.04. However, I didn't test pip on macOS and Windows

Use Docker
~~~~~~~~~~~~~~~~~
.. code::

    docker run -it \
    --user $(id -u) \
    -e DISPLAY=unix$DISPLAY \
    --workdir=$(pwd) \
    --volume="/home/$USER:/home/$USER" \
    --volume="/etc/group:/etc/group:ro" \
    --volume="/etc/passwd:/etc/passwd:ro" \
    --volume="/etc/shadow:/etc/shadow:ro" \
    --volume="/etc/sudoers.d:/etc/sudoers.d:ro" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    tzutalin/py2qt4

    make qt4py2;./labelImg.py

You can pull the image which has all of the installed and required dependencies. `Watch a demo video <https://youtu.be/nw1GexJzbCI>`__


Usage
-----

Steps
~~~~~

1. Build and launch using the instructions above.
2. Click 'Change default saved annotation folder' in Menu/File
3. Click 'Open Dir'
4. Click 'Create RectBox'
5. Click and release left mouse to select a region to annotate the rect
   box
6. You can use right mouse to drag the rect box to copy or move it

The annotation will be saved to the folder you specify.

You can refer to the below hotkeys to speed up your workflow.

Create pre-defined classes
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can edit the
`data/predefined\_classes.txt <https://github.com/tzutalin/labelImg/blob/master/data/predefined_classes.txt>`__
to load pre-defined classes

Hotkeys
~~~~~~~

+------------+--------------------------------------------+
| Ctrl + u   | Load all of the images from a directory    |
+------------+--------------------------------------------+
| Ctrl + r   | Change the default annotation target dir   |
+------------+--------------------------------------------+
| Ctrl + s   | Save                                       |
+------------+--------------------------------------------+
| Ctrl + d   | Copy the current label and rect box        |
+------------+--------------------------------------------+
| Space      | Flag the current image as verified         |
+------------+--------------------------------------------+
| w          | Create a base polygon                      |
+------------+--------------------------------------------+
| r          | Create an inner polygon                    |
+------------+--------------------------------------------+
| q          | edit inner polygon                         |
+------------+--------------------------------------------+
| t          | quit all the other create/edit             |
+------------+--------------------------------------------+
| c          | delete selected polygon                    |
+------------+--------------------------------------------+
| d          | Next image                                 |
+------------+--------------------------------------------+
| a          | Previous image                             |
+------------+--------------------------------------------+
| Ctrl++     | Zoom in                                    |
+------------+--------------------------------------------+
| Ctrl--     | Zoom out                                   |
+------------+--------------------------------------------+
| ↑→↓←       | Keyboard arrows to move selected rect box  |
+------------+--------------------------------------------+

FAQ:

1. you must select a base polygon so that you can create an inner polygon to it

2. you must select a base polygon so that you can edit its inner polygon 

3. press 'T' to quit the creat polygon / edit innerpolygon

4. you can choose the shape of the polygon when creating

多边形：    polygon
矩形：      rectangle
圆形：      circle
直线：      line
线段:       linestrip
斜矩形：    rectangle with an angle


