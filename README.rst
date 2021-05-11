Modern Relay
============

Welcome to Modern Relay's documentation! The intention for this project is to build a mail relay that works seamlessly in
the new IT landscape of cloud providers, API access, and the security measures that come with them. I've found that
federating Microsoft 365 tenants and requiring MFA for all accounts is a great leap forward in securing organizations,
but it introduces new strains on IT to integrate legacy devices/applications that an organization may not want to replace.

Modern Relay solves this problem by being a drop in replacement for the IIS-based SMTP relays that an organization
likely already has in place. There are configurable "delivery agents" that Modern Relay uses to convert mail coming in
from SMTP to different delivery schemes like an HTTP request to an API (e.g. Microsoft Graph). By leveraging APIs to
different mail providers, you can skip licensing hassles, 2FA/app password woes, custom Exchange Online connectors, and
adding another SPF address to your record.

Features
========

* Fully asynchronous
* Uses customizable delivery actions based on the origin IP address
* Queues mail in the event of delivery failure for later resending
* Access control to allow certain origin addresses/subnets or certain destination domains
* Supports anonymous and plain login schemes
* Supports STARTTLS if you provide the certs
* Supports Microsoft Graph API mail delivery

Requirements
============

You need **at least Python 3.6** to use this library

Supported Platforms
-------------------

``ModernRelay`` is tested on **CPython** and |PyPy3.7|_
for the following platforms:

* Windows 10
* Ubuntu 20.04
* Ubuntu 18.04

.. |PyPy3.7| replace:: **PyPy3.7**
.. _`PyPy3.7`: https://www.pypy.org/

Installation
============

For Linux or Windows environments where you're managing your own python installation, install with ``pip``::

    pip install modernrelay

You will need to set the appropriate environment variables for your chosen delivery agents. See individual agent
documentation for more details.

If an installer is more your speed, go download a Windows msi installer from the releases section and run it.

Building
========

You can install this package in a virtual environment like so::

    $ python3 -m venv /path/to/venv
    $ source /path/to/venv/bin/activate
    $ pip install -e .[dev]

License
=======

``ModernRelay`` is released under the MIT License.