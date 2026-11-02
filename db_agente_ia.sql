-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 29-06-2026 a las 02:18:44
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `db_agente_ia`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `log_escaneos`
--

CREATE TABLE `log_escaneos` (
  `id_escaneo` int(11) NOT NULL,
  `ruta_analizada` varchar(255) NOT NULL,
  `acceso_permitido` tinyint(1) NOT NULL,
  `total_carpetas` int(11) DEFAULT 0,
  `total_archivos` int(11) DEFAULT 0,
  `fecha_escaneo` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `log_escaneos`
--

INSERT INTO `log_escaneos` (`id_escaneo`, `ruta_analizada`, `acceso_permitido`, `total_carpetas`, `total_archivos`, `fecha_escaneo`) VALUES
(1, 'C:/Users/lliyo/OneDrive/Desktop/ricochet', 1, 0, 9, '2026-06-28 21:14:22'),
(2, 'C:/Users/lliyo/OneDrive/Desktop/Actividad_HTML_GarayRodrigo/img', 1, 0, 1, '2026-06-28 21:49:04'),
(3, 'C:/Users/lliyo/OneDrive/Desktop/ricochet', 1, 0, 9, '2026-06-28 21:58:46'),
(4, 'C:/Users/lliyo/OneDrive/Desktop', 1, 4, 21, '2026-06-29 00:17:03');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `log_escaneos`
--
ALTER TABLE `log_escaneos`
  ADD PRIMARY KEY (`id_escaneo`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `log_escaneos`
--
ALTER TABLE `log_escaneos`
  MODIFY `id_escaneo` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
