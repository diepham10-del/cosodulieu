-- =========================================
-- TẠO DATABASE
-- =========================================
CREATE DATABASE IF NOT EXISTS cinema_management;

USE cinema_management;

-- =========================================
-- BẢNG CINEMA
-- =========================================
CREATE TABLE IF NOT EXISTS Cinema (
    cinema_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    location VARCHAR(100)
);

-- =========================================
-- BẢNG MOVIE
-- =========================================
CREATE TABLE IF NOT EXISTS Movie (
    movie_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100),
    duration INT,
    genre VARCHAR(50)
);

-- =========================================
-- BẢNG ROOM
-- =========================================
CREATE TABLE IF NOT EXISTS Room (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    cinema_id INT,
    name VARCHAR(50),
    capacity INT,
    FOREIGN KEY (cinema_id) REFERENCES Cinema (cinema_id)
);

-- =========================================
-- BẢNG SEAT (KHÓA KÉP)
-- =========================================
CREATE TABLE IF NOT EXISTS Seat (
    room_id INT,
    seat_number VARCHAR(10),
    PRIMARY KEY (room_id, seat_number),
    FOREIGN KEY (room_id) REFERENCES Room (room_id)
);

-- =========================================
-- BẢNG SHOWTIME
-- =========================================
CREATE TABLE IF NOT EXISTS ShowTime (
    showtime_id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT,
    room_id INT,
    start_time DATETIME,
    FOREIGN KEY (movie_id) REFERENCES Movie (movie_id),
    FOREIGN KEY (room_id) REFERENCES Room (room_id)
);

-- =========================================
-- BẢNG CUSTOMER
-- =========================================
CREATE TABLE IF NOT EXISTS Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    phone VARCHAR(20)
);

-- =========================================
-- BẢNG BOOKING (GIỐNG DOI HINH)
-- =========================================
CREATE TABLE IF NOT EXISTS Booking (
    showtime_id INT,
    customer_id INT,
    booking_time DATETIME,
    PRIMARY KEY (showtime_id, customer_id),
    FOREIGN KEY (showtime_id) REFERENCES ShowTime (showtime_id),
    FOREIGN KEY (customer_id) REFERENCES Customer (customer_id)
);

-- =========================================
-- BẢNG BOOKING DETAIL (GIỐNG THAM GIA)
-- =========================================
CREATE TABLE IF NOT EXISTS BookingDetail (
    showtime_id INT,
    room_id INT,
    seat_number VARCHAR(10),
    price FLOAT,
    PRIMARY KEY (
        showtime_id,
        room_id,
        seat_number
    ),
    FOREIGN KEY (showtime_id) REFERENCES ShowTime (showtime_id),
    FOREIGN KEY (room_id, seat_number) REFERENCES Seat (room_id, seat_number)
);

-- =========================================
-- TRIGGER 1: KHÔNG TRÙNG GHẾ
-- =========================================
DELIMITER $$

CREATE TRIGGER no_duplicate_seat
BEFORE INSERT ON BookingDetail
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM BookingDetail
        WHERE showtime_id = NEW.showtime_id
        AND room_id = NEW.room_id
        AND seat_number = NEW.seat_number
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ghe da duoc dat';
    END IF;
END$$

DELIMITER;

-- =========================================
-- TRIGGER 2: GIỚI HẠN GHẾ / PHÒNG
-- =========================================
DELIMITER $$

CREATE TRIGGER limit_seat
AFTER INSERT ON Seat
FOR EACH ROW
BEGIN
    DECLARE seat_count INT;

    SELECT COUNT(*) INTO seat_count
    FROM Seat
    WHERE room_id = NEW.room_id;

    IF seat_count > 100 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Moi phong toi da 100 ghe';
    END IF;
END$$

DELIMITER;

-- =========================================
-- TRIGGER 3: GIỚI HẠN SUẤT / NGÀY
-- =========================================
DELIMITER $$

CREATE TRIGGER limit_showtime
BEFORE INSERT ON ShowTime
FOR EACH ROW
BEGIN
    DECLARE show_count INT;

    SELECT COUNT(*) INTO show_count
    FROM ShowTime
    WHERE room_id = NEW.room_id
    AND DATE(start_time) = DATE(NEW.start_time);

    IF show_count >= 10 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Moi phong toi da 10 suat/ngay';
    END IF;
END$$

DELIMITER;

-- =========================================
-- TRIGGER 4: CHECK GIÁ VÉ
-- =========================================
DELIMITER $$

CREATE TRIGGER check_price
BEFORE INSERT ON BookingDetail
FOR EACH ROW
BEGIN
    IF NEW.price <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Gia ve phai > 0';
    END IF;
END$$

DELIMITER;