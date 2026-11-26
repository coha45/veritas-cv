// Initial UI configuration so the controls render before the broker's first
// TOPDOWN snapshot arrives. The broker's traffic_checkers.json remains the
// runtime source of truth and replaces this list when it connects.
export const defaultTrafficCheckers = [
  {
    id: 'north_road',
    label: 'North road',
    approach_zones: ['middle_left_lane', 'middle_right_lane'],
    gpio_pins: [17, 27],
  },
  {
    id: 'west_road',
    label: 'West road',
    approach_zones: ['left_left_lane', 'left_right_lane'],
    gpio_pins: [22, 5],
  },
  {
    id: 'east_road',
    label: 'East road',
    approach_zones: ['right_left_lane', 'right_right_lane'],
    gpio_pins: [6, 13],
  },
]
