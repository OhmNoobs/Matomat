-- Product table
DROP TABLE IF EXISTS Products;
CREATE TABLE Products
(
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  image TEXT,
  color TEXT
);
CREATE UNIQUE INDEX Products_id_uindex ON Products (id);
CREATE UNIQUE INDEX Products_name_uindex ON Products (name);

-- User table
DROP TABLE IF EXISTS Users;
CREATE TABLE Users
(
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  name TEXT,
  card_id INTEGER NOT NULL
);
CREATE UNIQUE INDEX Users_id_uindex ON Users (id);
CREATE UNIQUE INDEX Users_card_id_uindex ON Users (card_id);
INSERT INTO Users (name, card_id) VALUES ('Fachschaft', 0);

-- Transaction table
DROP TABLE IF EXISTS Transactions;
CREATE TABLE Transactions
(
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  "from" INTEGER NOT NULL,
  "to" INTEGER NOT NULL,
  timestamp TEXT NOT NULL,
  CONSTRAINT transactions_Users_id_fk FOREIGN KEY ("from") REFERENCES Users (id) ON UPDATE CASCADE,
  CONSTRAINT transactions_Users_id_fk FOREIGN KEY ("to") REFERENCES Users (id) ON UPDATE CASCADE
);
CREATE UNIQUE INDEX transactions_id_uindex ON transactions (id);

-- Items to transactions table
DROP TABLE IF EXISTS Transaction_Products;
CREATE TABLE Transaction_Products
(
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  "transaction" INTEGER NOT NULL,
  product INTEGER NOT NULL,
  CONSTRAINT Transaction_Products_Transactions_id_fk FOREIGN KEY ("transaction") REFERENCES Transactions (id),
  CONSTRAINT Transaction_Products_Products_id_fk FOREIGN KEY (product) REFERENCES Products (id)
);
CREATE UNIQUE INDEX Transaction_Products_id_uindex ON Transaction_Products (id);
