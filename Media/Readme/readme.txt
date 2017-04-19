HELLO ACI
=====================


# Introduction

This application aims at providing a toy example as a stateful app. It shows in the APIC's GUI the tenants of the system.


# Components

This application is composed of:
- a frontend: web UI displaying the tenants, see the UIAssets/ directory,
- a backend: docker container that queries the APIC to retrive the tenants, see the Service/ directory.


# Workflow

The workflow for this application is the following:

1. The user opens the application. This triggers a request from the frontend towards the backend:

        APIC IP/appcenter/Cisco/HelloAciStateful/getTenant.json

2. At the backend side, upon reception of this request, the web server queries the APIC for the tenants ('fvTenant').

3. Upon reception of the reply from the APIC, the web server forges a response containing those tenants.

4. The frontend receives this response, reads it and generates a graph showing the different tenants. 