class Zone {
    constructor(zone_type, name, zone_direction) {
        this.zone_type = zone_type
        this.name = name
        this.zone_direction = zone_direction
    } 
    tableDisplay() { 
        return this.name + " - " + this.zone_type + " - " + this.zone_direction
    }
}

export default Zone