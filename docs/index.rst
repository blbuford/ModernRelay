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


.. automodule:: ModernRelay.modern_relay
    :members:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   development


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
