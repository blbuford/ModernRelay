 * Configurable inbound peers
    * Allow an IP address or subnet
    * Choose type of auth: 
      * Anonymous (no pw)
      * Basic Auth (username/pw validated against sql lite)
      * STRETCH GOAL: Basic Auth against LDAP/KRB (Like active directory)
    * Choose allowed destinations:
      * Allow all
      * Domain list
    * Choose delivery agent:
      * MS Graph
      * Basic SMTP:
        * Smart host
        * MX record (default)
        * STRETCH GOAL: Do destination cert checking like an Exchange connector would
* Inbound SSL/TLS
* Delivery Agents:
    * MS Graph
    * Basic STMP
    * Maybe GSuite/Google