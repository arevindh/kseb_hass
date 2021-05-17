# A Home Assistant custom component to get your KESB Bill Amount, Units consumed and Due Date information.
To get started put all the files from/custom_components/kseb/ here: <config directory>/custom_components/kseb/

Example configuration.yaml:

```sensor:
  - platform: kseb
    consumerno: 1234567890 
    username: myusername
    password: mypassword
    scan_interval: 86400
