export interface GeoCoordinate {
  lng: number
  lat: number
}

export interface CampusProfile {
  name: string
  shortName: string
  address: string
  /** 行政区划代码，用于高德实况天气。 */
  adcode: string
  defaultZoom: number
  center: {
    gcj02: GeoCoordinate
    wgs84: GeoCoordinate
  }
}

/**
 * 当前部署的校园地理基准。
 *
 * - GCJ-02 用于高德/腾讯等国内地图。
 * - WGS84 用于 GeoJSON、Leaflet 和 OpenStreetMap。
 * - 地图 API 和 GeoJSON 均按 [经度, 纬度] 顺序传值。
 */
export const campusProfile: CampusProfile = {
  name: '四川现代职业学院',
  shortName: '四川现代职院',
  address: '四川省成都市西南航空港双华路三段华创路 1 号',
  adcode: '510116',
  defaultZoom: 17,
  center: {
    gcj02: { lng: 103.997424, lat: 30.515862 },
    wgs84: { lng: 103.995133, lat: 30.518507 },
  },
}

export function formatCoordinate(point: GeoCoordinate): string {
  return `${point.lng.toFixed(6)}°E · ${point.lat.toFixed(6)}°N`
}
