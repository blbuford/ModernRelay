 * Configurable inbound peers
    * (cidr_address) Allow an IP address or subnet
    * (authentication) Choose type of auth: 
      * Anonymous (no pw) (default, if unset)
      * Basic Auth (username/pw validated against sql lite)
      * STRETCH GOAL: Basic Auth against LDAP/KRB (Like active directory)
    * (destination) Choose allowed destinations:
      * Allow all (default, if unset)
      * Domain list
    * (agent) Choose delivery agent:
      * MS Graph
      * Basic SMTP:
        * Smart host
        * MX record (default)
        * STRETCH GOAL: Do destination cert checking like an Exchange connector would
      * (tls)
        * required: yes/no
        * public key
        * private key
* Inbound SSL/TLS
* Delivery Agents:
    * MS Graph
    * Basic SMTP
    * Maybe GSuite/Google