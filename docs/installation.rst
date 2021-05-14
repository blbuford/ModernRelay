Installation
============

As mentioned in the README, the goal is to make this package easy to install and use. Manual installation for either
platform is straight forward:

Windows
-------
Like anything else in IT, there are many ways to setup this program and have it work as intended. If you're familiar
with Python environments, feel free set this up manually. If not, no worries, a Windows installer is provided. This
installer includes its own copy of Python 3.9 and does a couple of neat things for you:

* It will install a distributable executable with its dependencies into your Program Files directory
* It will setup a folder structure in ProgramData which it uses for logging and the mail spool
* It will configure |NSSM|_ for use with Modern Relay and install it as a service
* It will configure that service to use a virtual service account: ``NT SERVICE\ModernRelay``
* It will prompt for and set the environment variables for that service such that you can the appropriate delivery agents

If you're using the Microsoft 365 mail delivery agent, you will need to provide your Tenant ID, App ID, and App Secret.
If you've never created those before, you can follow the |how-to-create-service-principal-portal|_ to get that information.

Once you've clicked **next** enough times and filled in the appropriate details, you'll have Modern Relay installed and
ready to go! Modern Relay does not contain a graphical interface. You can interact with it by starting/stopping its
service and changing its ``config.yaml`` file located in the ``Program Files\ModernRelay`` directory. See the usage
documentation for more details on ``config.yaml``.


.. |NSSM| replace:: **NSSM**
.. _`NSSM`: https://nssm.cc/
.. |how-to-create-service-principal-portal| replace:: **Microsoft documentation**
.. _`how-to-create-service-principal-portal`: https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal

