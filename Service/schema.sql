CREATE TABLE vmware (
    id INTEGER NOT NULL, 
    vcenter CHAR(25) NOT NULL,
    username CHAR(32) NOT NULL,
    password CHAR(32) NOT NULL,
    PRIMARY KEY (id)
)