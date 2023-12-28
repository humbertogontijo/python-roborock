Usage
=====

Installation
------------

To use Python-Roborock, first install it using pip:

.. code-block:: console

   (.venv) $ pip install python-roborock

Login
-----

.. code-block:: console

      (.venv) $ roborock login --email username --password password

List devices
------------

This will list all devices associated with the account:

.. code-block:: console

   (.venv) $ roborock list-devices

   Known devices MyRobot: 7kI9d66UoPXd6sd9gfd75W


The deviceId 7kI9d66UoPXd6sd9gfd75W can be used to run commands on the device.

Run a command
-------------

To run a command:

.. code-block:: console

   (.venv) $ roborock -d command --device_id 7kI9d66UoPXd6sd9gfd75W --cmd get_status
