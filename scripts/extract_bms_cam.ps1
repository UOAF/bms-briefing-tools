param(
    [Parameter(Mandatory = $true)]
    [string]$CamPath,

    [string]$BmsRoot = "C:\Falcon BMS 4.38",

    [string]$ObjectDir = "",

    [int]$Version = 0,

    [string]$OutputPath = ""
)

# Legacy read-only compatibility decoder. BMSUtils is useful for extraction and
# regression comparison, but known write-back bugs make it unsuitable as a
# future campaign serialization path.

if ([Environment]::Is64BitProcess) {
    $ps32 = Join-Path $env:WINDIR "SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path $ps32) {
        $arguments = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $PSCommandPath,
            "-CamPath", $CamPath,
            "-BmsRoot", $BmsRoot
        )
        if ($ObjectDir) {
            $arguments += @("-ObjectDir", $ObjectDir)
        }
        if ($Version -gt 0) {
            $arguments += @("-Version", $Version)
        }
        if ($OutputPath) {
            $arguments += @("-OutputPath", $OutputPath)
        }
        & $ps32 @arguments
        exit $LASTEXITCODE
    }
}

$ErrorActionPreference = "Stop"

function Clean-BmsString {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) {
        return $null
    }
    return $Value.Split([char]0)[0].Trim()
}

function Get-VuId {
    param([Parameter(Mandatory = $true)]$Value)
    $num = [uint64]$Value.num_
    $creator = [uint64]$Value.creator_
    return [ordered]@{
        num = $num
        creator = $creator
        key = "$num`:$creator"
    }
}

function Get-EnumName {
    param(
        [Parameter(Mandatory = $true)][string]$TypeName,
        [Parameter(Mandatory = $true)][int]$Value
    )
    $type = $script:BmsAssembly.GetType($TypeName)
    if ($null -eq $type) {
        return $null
    }
    try {
        return ([Enum]::ToObject($type, $Value)).ToString()
    }
    catch {
        return $null
    }
}

function Get-ShortMissionName {
    param([AllowNull()][string]$Name)
    if (-not $Name) {
        return $null
    }
    return ($Name -replace "^AMIS_", "")
}

function Read-Callsigns {
    param([Parameter(Mandatory = $true)][string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) {
        return $map
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed -split "\s+", 2
        if ($parts.Count -lt 2) {
            continue
        }
        $id = 0
        if ([int]::TryParse($parts[0], [ref]$id)) {
            $map[$id] = $parts[1].Trim()
        }
    }
    return $map
}

function Read-TheaterCallsigns {
    param([Parameter(Mandatory = $true)][string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) {
        return $map
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed -split "\s+", 2
        if ($parts.Count -lt 2) {
            continue
        }
        $stringId = 0
        if ([int]::TryParse($parts[0], [ref]$stringId) -and $stringId -ge 2000) {
            $callsignId = $stringId - 2000
            $name = $parts[1].Trim()
            if ($name) {
                $map[$callsignId] = $name
            }
        }
    }
    return $map
}

function Merge-Callsigns {
    param(
        [Parameter(Mandatory = $true)]$Primary,
        [Parameter(Mandatory = $true)]$Fallback
    )
    $map = @{}
    foreach ($key in $Fallback.Keys) {
        $map[$key] = $Fallback[$key]
    }
    foreach ($key in $Primary.Keys) {
        $map[$key] = $Primary[$key]
    }
    return $map
}

function Read-CamDirectory {
    param([Parameter(Mandatory = $true)][byte[]]$Data)
    $directorOffset = [BitConverter]::ToUInt32($Data, 0)
    $declaredCount = [BitConverter]::ToUInt32($Data, [int]$directorOffset)
    $count = [Math]::Min([int]$declaredCount, 12)
    $pos = [int]$directorOffset + 4
    $entries = @()
    for ($i = 0; $i -lt $count; $i++) {
        $nameLength = $Data[$pos]
        $pos++
        $name = [Text.Encoding]::Default.GetString($Data, $pos, $nameLength)
        $pos += $nameLength
        $offset = [BitConverter]::ToUInt32($Data, $pos)
        $pos += 4
        $size = [BitConverter]::ToUInt32($Data, $pos)
        $pos += 4
        $entries += [pscustomobject][ordered]@{
            index = $i
            name = $name
            extension = [IO.Path]::GetExtension($name).ToLowerInvariant()
            offset = [int]$offset
            size = [int]$size
            end = [int]($offset + $size)
        }
    }
    return [ordered]@{
        director_offset = [int]$directorOffset
        declared_file_count = [int]$declaredCount
        entry_count = [int]$count
        directory_end = [int]$pos
        entries = @($entries)
    }
}

function Get-SectionBytes {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Data,
        [Parameter(Mandatory = $true)]$Entry
    )
    $bytes = New-Object byte[] $Entry.size
    [Array]::Copy($Data, $Entry.offset, $bytes, 0, $Entry.size)
    return $bytes
}

function Convert-Waypoint {
    param(
        [Parameter(Mandatory = $true)]$Waypoint,
        [Parameter(Mandatory = $true)][int]$Index
    )
    $actionName = Get-EnumName "BMSUtils.F4Structs+WptAction" ([int]$Waypoint.Action)
    return [ordered]@{
        index = $Index
        grid_x = [int]$Waypoint.GridX
        grid_y = [int]$Waypoint.GridY
        grid_z = [int]$Waypoint.GridZ
        arrive = [uint64]$Waypoint.Arrive
        depart = [uint64]$Waypoint.Depart
        action = [int]$Waypoint.Action
        action_name = $actionName
        route_action = [int]$Waypoint.RouteAction
        speed = [uint64]$Waypoint.Speed
        flags = [uint64]$Waypoint.Flags
        target_id = (Get-VuId $Waypoint.TargetID)
        target_building = [int]$Waypoint.TargetBuilding
    }
}

function Convert-Waypoints {
    param([AllowNull()]$Waypoints)
    $items = @()
    if ($null -eq $Waypoints) {
        return @()
    }
    for ($i = 0; $i -lt $Waypoints.Length; $i++) {
        if ($null -ne $Waypoints[$i]) {
            $items += (Convert-Waypoint $Waypoints[$i] $i)
        }
    }
    return @($items)
}

function Convert-CommonUnit {
    param([Parameter(Mandatory = $true)]$Unit)
    return [ordered]@{
        id = (Get-VuId $Unit.id)
        type = $Unit.GetType().Name
        entity_type = [int]$Unit.entityType
        camp_id = [int]$Unit.campId
        name_id = [int]$Unit.name_id
        owner = [int]$Unit.owner
        x = [int]$Unit.x
        y = [int]$Unit.y
        z = [double]$Unit.z
        roster = [int]$Unit.roster
        unit_flags = [int]$Unit.unit_flags
        current_wp = [int]$Unit.current_wp
        num_waypoints = [int]$Unit.numWaypoints
    }
}

function Convert-Team {
    param([Parameter(Mandatory = $true)]$Team)
    return [ordered]@{
        who = [int]$Team.who
        cteam = [int]$Team.cteam
        flags = [int]$Team.flags
        team_flag = [int]$Team.teamFlag
        team_color = [int]$Team.teamColor
        equipment = [int]$Team.equipment
        name = (Clean-BmsString $Team.name)
        air_experience = [int]$Team.airExperience
        air_defense_experience = [int]$Team.airDefenseExperience
        ground_experience = [int]$Team.groundExperience
        naval_experience = [int]$Team.navalExperience
        initiative = [int]$Team.initiative
        supply_available = [int]$Team.supplyAvail
        fuel_available = [int]$Team.fuelAvail
        replacements_available = [int]$Team.replacementsAvail
        member = @($Team.member | ForEach-Object { [int]$_ })
        stance = @($Team.stance | ForEach-Object { [int]$_ })
    }
}

function Convert-ObjectiveDelta {
    param([Parameter(Mandatory = $true)]$Delta)
    return [ordered]@{
        id = (Get-VuId $Delta.id)
        last_repair = [uint64]$Delta.last_repair
        owner = [int]$Delta.owner
        supply = [int]$Delta.supply
        fuel = [int]$Delta.fuel
        losses = [int]$Delta.losses
        fstatus_count = [int]$Delta.numFstatus
        fstatus = @($Delta.fStatus | ForEach-Object { [int]$_ })
    }
}

function Convert-ClockMs {
    param([Parameter(Mandatory = $true)][uint64]$Milliseconds)
    $totalMinutes = [Math]::Floor(([double]($Milliseconds % 86400000)) / 60000.0)
    $hours = [Math]::Floor($totalMinutes / 60)
    $minutes = $totalMinutes % 60
    return "{0:D2}{1:D2}" -f [int]$hours, [int]$minutes
}

function Decode-CampaignClock {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Data,
        [Parameter(Mandatory = $true)]$Entry
    )
    if ($Entry.size -lt 8) {
        return $null
    }
    $compressedSize = [BitConverter]::ToInt32($Data, $Entry.offset)
    $decompressedSize = [BitConverter]::ToInt32($Data, $Entry.offset + 4)
    if ($compressedSize -le 0 -or $decompressedSize -le 0) {
        return $null
    }
    $payload = New-Object byte[] $compressedSize
    [Array]::Copy($Data, $Entry.offset + 8, $payload, 0, $compressedSize)
    $expanded = [Lzss.Codec]::Decompress($payload, $decompressedSize)
    $campaignTime = [BitConverter]::ToUInt32($expanded, 0)
    $timeStep = [BitConverter]::ToUInt32($expanded, 4)
    $clockBase = [BitConverter]::ToUInt32($expanded, 8)
    return [ordered]@{
        compressed_size = [int]$compressedSize
        decompressed_size = [int]$decompressedSize
        campaign_time_ms = [uint64]$campaignTime
        time_step_ms = [uint64]$timeStep
        clock_base_ms = [uint64]$clockBase
        clock_base_hhmm = Convert-ClockMs $clockBase
        note = "Inferred from the first three int32 values of the decompressed .cmp section."
    }
}

function Convert-Squadron {
    param([Parameter(Mandatory = $true)]$Squadron)
    $common = Convert-CommonUnit $Squadron
    $common.airbase_id = Get-VuId $Squadron.airbase_id
    $common.fuel = [int]$Squadron.fuel
    $common.specialty = [int]$Squadron.specialty
    $common.missions_flown = [int]$Squadron.missions_flown
    $common.total_losses = [int]$Squadron.total_losses
    $common.squadron_patch = [int]$Squadron.squadron_patch
    $common.squadron_name = Clean-BmsString $Squadron.squadronName
    return $common
}

function Convert-Battalion {
    param([Parameter(Mandatory = $true)]$Battalion)
    $common = Convert-CommonUnit $Battalion
    $common.parent_id = Get-VuId $Battalion.parent_id
    $common.last_obj = Get-VuId $Battalion.last_obj
    $common.left_front = [ordered]@{ x = [int]$Battalion.lfx; y = [int]$Battalion.lfy }
    $common.right_front = [ordered]@{ x = [int]$Battalion.rfx; y = [int]$Battalion.rfy }
    $common.supply = [int]$Battalion.supply
    $common.fatigue = [int]$Battalion.fatigue
    $common.morale = [int]$Battalion.morale
    $common.heading = [int]$Battalion.heading
    $common.final_heading = [int]$Battalion.final_heading
    $common.position = [int]$Battalion.position
    return $common
}

function Convert-Brigade {
    param([Parameter(Mandatory = $true)]$Brigade)
    $common = Convert-CommonUnit $Brigade
    $common.elements = [int]$Brigade.elements
    $common.element_ids = @($Brigade.element | Where-Object { $null -ne $_ } | ForEach-Object { Get-VuId $_ })
    return $common
}

function Convert-TaskForce {
    param([Parameter(Mandatory = $true)]$TaskForce)
    $common = Convert-CommonUnit $TaskForce
    $common.orders = [int]$TaskForce.orders
    $common.supply = [int]$TaskForce.supply
    return $common
}

function Convert-Package {
    param([Parameter(Mandatory = $true)]$Package)
    $common = Convert-CommonUnit $Package
    $missionName = Get-EnumName "BMSUtils.F4Structs+MissionTypeEnum" ([int]$Package.mis_request.mission)
    $common.elements = [int]$Package.elements
    $common.element_ids = @($Package.element | Where-Object { $null -ne $_ } | ForEach-Object { Get-VuId $_ })
    $common.awacs_id = Get-VuId $Package.awacs
    $common.jstar_id = Get-VuId $Package.jstar
    $common.ecm_id = Get-VuId $Package.ecm
    $common.tanker_id = Get-VuId $Package.tanker
    $common.interceptor_id = Get-VuId $Package.interceptor
    $common.cargo_id = Get-VuId $Package.cargo_id
    $common.flights = [int]$Package.flights
    $common.takeoff = [uint64]$Package.takeoff
    $common.target_time = [uint64]$Package.tp_time
    $common.package_flags = [uint64]$Package.package_flags
    $common.ingress_point = [ordered]@{ x = [int]$Package.iax; y = [int]$Package.iay }
    $common.egress_point = [ordered]@{ x = [int]$Package.eax; y = [int]$Package.eay }
    $common.target_point = [ordered]@{ x = [int]$Package.tpx; y = [int]$Package.tpy }
    $common.ingress_waypoints = Convert-Waypoints $Package.ingress_waypoints
    $common.egress_waypoints = Convert-Waypoints $Package.egress_waypoints
    $common.mission_request = [ordered]@{
        mission = [int]$Package.mis_request.mission
        mission_name = $missionName
        mission_short = Get-ShortMissionName $missionName
        aircraft = [int]$Package.mis_request.aircraft
        context = [int]$Package.mis_request.context
        tot = [uint64]$Package.mis_request.tot
        tx = [int]$Package.mis_request.tx
        ty = [int]$Package.mis_request.ty
        target_id = (Get-VuId $Package.mis_request.targetID)
        requester_id = (Get-VuId $Package.mis_request.requesterID)
        priority = [int]$Package.mis_request.priority
    }
    return $common
}

function Convert-Loadout {
    param([AllowNull()]$Loadout)
    if ($null -eq $Loadout) {
        return $null
    }
    return [ordered]@{
        weapon_ids = @($Loadout.WeaponID | ForEach-Object { [int]$_ })
        weapon_counts = @($Loadout.WeaponCount | ForEach-Object { [int]$_ })
    }
}

function Get-AircraftCountFromRoster {
    param([Parameter(Mandatory = $true)][int]$Roster)
    $count = 0
    for ($i = 0; $i -lt 16; $i++) {
        $count += (($Roster -shr (2 * $i)) -band 3)
    }
    return [int]$count
}

function Convert-Flight {
    param(
        [Parameter(Mandatory = $true)]$Flight,
        [Parameter(Mandatory = $true)]$CallsignMap,
        [Parameter(Mandatory = $true)]$SquadronMap,
        [Parameter(Mandatory = $true)]$PackageMap
    )
    $common = Convert-CommonUnit $Flight
    $missionName = Get-EnumName "BMSUtils.F4Structs+MissionTypeEnum" ([int]$Flight.mission)
    $oldMissionName = Get-EnumName "BMSUtils.F4Structs+MissionTypeEnum" ([int]$Flight.old_mission)
    $callsignName = $CallsignMap[[int]$Flight.callsign_id]
    $packageId = Get-VuId $Flight.package
    $squadronId = Get-VuId $Flight.squadron
    $common.mission = [int]$Flight.mission
    $common.mission_name = $missionName
    $common.mission_short = Get-ShortMissionName $missionName
    $common.old_mission = [int]$Flight.old_mission
    $common.old_mission_name = $oldMissionName
    $common.time_on_target = [uint64]$Flight.time_on_target
    $common.mission_over_time = [uint64]$Flight.mission_over_time
    $common.mission_target = [int]$Flight.mission_target
    $common.mission_id = [int]$Flight.mission_id
    $common.mission_context = [int]$Flight.mission_context
    $common.requester_id = Get-VuId $Flight.requester
    $common.aircraft_count = Get-AircraftCountFromRoster ([int]$Flight.roster)
    $common.plane_stats = @($Flight.plane_stats | ForEach-Object { [int]$_ })
    $common.last_player_slot = [int]$Flight.last_player_slot
    $common.player_slots = @($Flight.player_slots | ForEach-Object { [int]$_ })
    $common.use_loadout = [int]$Flight.use_loadout
    $common.loadout_count = [int]$Flight.loadouts
    $common.loadouts = @($Flight.loadout | Where-Object { $null -ne $_ } | ForEach-Object { Convert-Loadout $_ })
    $common.weapon_ids = @($Flight.weapon | ForEach-Object { [int]$_ })
    $common.weapon_counts = @($Flight.weapons | ForEach-Object { [int]$_ })
    $common.laser_codes = @($Flight.laserCode | ForEach-Object { [int]$_ })
    $common.loaded_cft = @($Flight.Loaded_CFT | ForEach-Object { [bool]$_ })
    $common.callsign_id = [int]$Flight.callsign_id
    $common.callsign_name = $callsignName
    $common.callsign_num = [int]$Flight.callsign_num
    $common.callsign = if ($callsignName) { "$callsignName $($Flight.callsign_num)" } else { $null }
    $common.package_id = $packageId
    $common.package_camp_id = if ($PackageMap.ContainsKey($packageId.key)) { [int]$PackageMap[$packageId.key].camp_id } else { $null }
    $common.squadron_id = $squadronId
    $common.squadron_camp_id = if ($SquadronMap.ContainsKey($squadronId.key)) { [int]$SquadronMap[$squadronId.key].camp_id } else { $null }
    $common.squadron_name = if ($SquadronMap.ContainsKey($squadronId.key)) { $SquadronMap[$squadronId.key].squadron_name } else { $null }
    $common.tacan = @(
        for ($i = 0; $i -lt $Flight.TacanChannel.Length; $i++) {
            [ordered]@{
                slot = $i
                channel = [int]$Flight.TacanChannel[$i]
                band = [int]$Flight.TacanBand[$i]
            }
        }
    )
    $common.pilots = @($Flight.pilots | ForEach-Object { [int]$_ })
    $common.slots = @($Flight.slots | ForEach-Object { [int]$_ })
    $common.waypoints = Convert-Waypoints $Flight.waypoints
    return $common
}

$resolvedCamPath = (Resolve-Path -LiteralPath $CamPath).Path
$resolvedBmsRoot = (Resolve-Path -LiteralPath $BmsRoot).Path
if (-not $ObjectDir) {
    $ObjectDir = Join-Path $resolvedBmsRoot "Data\TerrData\Objects"
}
$resolvedObjectDir = (Resolve-Path -LiteralPath $ObjectDir).Path
if (-not $resolvedObjectDir.EndsWith("\")) {
    $resolvedObjectDir += "\"
}

$lzssPath = Join-Path $resolvedBmsRoot "mc\LzssManaged.dll"
$bmsUtilsPath = Join-Path $resolvedBmsRoot "mc\BMSUtils.dll"
[Reflection.Assembly]::LoadFrom($lzssPath) | Out-Null
$script:BmsAssembly = [Reflection.Assembly]::LoadFrom($bmsUtilsPath)

$data = [IO.File]::ReadAllBytes($resolvedCamPath)
$directory = Read-CamDirectory $data
$entryByExtension = @{}
foreach ($entry in $directory.entries) {
    $entryByExtension[$entry.extension] = $entry
}
if ($Version -le 0 -and $entryByExtension.ContainsKey(".ver")) {
    $verBytes = Get-SectionBytes $data $entryByExtension[".ver"]
    $versionText = [Text.Encoding]::ASCII.GetString($verBytes).Trim()
    $parsedVersion = 0
    if ([int]::TryParse($versionText, [ref]$parsedVersion)) {
        $Version = $parsedVersion
    }
}
if ($Version -le 0) {
    throw "Could not determine BMS save version. Pass -Version explicitly."
}

$campaignDir = Split-Path -Parent $resolvedCamPath
$theaterCallsigns = Read-TheaterCallsigns (Join-Path $campaignDir "Strings.txt")
$oldCallsigns = Read-Callsigns (Join-Path $resolvedBmsRoot "mc\OldCallsigns.txt")
$callsigns = Merge-Callsigns $theaterCallsigns $oldCallsigns

$campaignClock = $null
if ($entryByExtension.ContainsKey(".cmp")) {
    $campaignClock = Decode-CampaignClock $data $entryByExtension[".cmp"]
}

$teams = @()
if ($entryByExtension.ContainsKey(".tea")) {
    $teaBytes = Get-SectionBytes $data $entryByExtension[".tea"]
    $teaFile = [BMSUtils.TeaFile]::new($teaBytes, $Version)
    foreach ($team in $teaFile.teams) {
        if ($null -ne $team) {
            $teams += (Convert-Team $team)
        }
    }
}

$objectiveDeltas = @()
if ($entryByExtension.ContainsKey(".obd")) {
    $obdBytes = Get-SectionBytes $data $entryByExtension[".obd"]
    $obdFile = [BMSUtils.ObdFile]::new($obdBytes, $Version)
    foreach ($delta in $obdFile.deltas) {
        if ($null -ne $delta) {
            $objectiveDeltas += (Convert-ObjectiveDelta $delta)
        }
    }
}

$unitCounts = [ordered]@{}
$squadrons = @()
$packages = @()
$flights = @()
$battalions = @()
$brigades = @()
$taskForces = @()
$missionCounts = [ordered]@{}
$classTableCount = 0

if ($entryByExtension.ContainsKey(".uni")) {
    $readXml = $true
    $classTablePath = Join-Path $resolvedObjectDir "Falcon4_CT.xml"
    $classTable = [BMSUtils.ClassTable]::new().LoadCT($resolvedObjectDir, $classTablePath, [ref]$readXml)
    if ($null -eq $classTable) {
        throw "Could not load Falcon4 class table from $resolvedObjectDir"
    }
    $classTableCount = $classTable.Length
    $uniBytes = Get-SectionBytes $data $entryByExtension[".uni"]
    $uniFile = [BMSUtils.UniFile]::new($uniBytes, $Version, $classTable, $false)
    $units = @($uniFile.units | Where-Object { $null -ne $_ })
    foreach ($group in ($units | Group-Object { $_.GetType().Name } | Sort-Object Name)) {
        $unitCounts[$group.Name] = [int]$group.Count
    }

    foreach ($battalion in ($units | Where-Object { $_.GetType().Name -eq "Battalion" })) {
        $battalions += (Convert-Battalion $battalion)
    }

    foreach ($brigade in ($units | Where-Object { $_.GetType().Name -eq "Brigade" })) {
        $brigades += (Convert-Brigade $brigade)
    }

    foreach ($taskForce in ($units | Where-Object { $_.GetType().Name -eq "TaskForce" })) {
        $taskForces += (Convert-TaskForce $taskForce)
    }

    $squadronMap = @{}
    foreach ($squadron in ($units | Where-Object { $_.GetType().Name -eq "Squadron" })) {
        $converted = Convert-Squadron $squadron
        $squadrons += $converted
        $squadronMap[$converted.id.key] = $converted
    }

    $packageMap = @{}
    foreach ($package in ($units | Where-Object { $_.GetType().Name -eq "Package" })) {
        $converted = Convert-Package $package
        $packages += $converted
        $packageMap[$converted.id.key] = $converted
    }

    foreach ($flight in ($units | Where-Object { $_.GetType().Name -eq "Flight" })) {
        $converted = Convert-Flight $flight $callsigns $squadronMap $packageMap
        $flights += $converted
        $missionKey = if ($converted.mission_short) { $converted.mission_short } else { [string]$converted.mission }
        if (-not $missionCounts.Contains($missionKey)) {
            $missionCounts[$missionKey] = 0
        }
        $missionCounts[$missionKey] = [int]$missionCounts[$missionKey] + 1
    }
}

$result = [ordered]@{
    source = [ordered]@{
        cam_path = $resolvedCamPath
        bms_root = $resolvedBmsRoot
        object_dir = $resolvedObjectDir
        bmsutils = $bmsUtilsPath
        save_version = $Version
        class_table_entries = $classTableCount
        callsign_strings = (Join-Path $campaignDir "Strings.txt")
        callsign_count = $callsigns.Count
    }
    directory = $directory
    campaign_clock = $campaignClock
    teams = @($teams)
    objective_deltas = @($objectiveDeltas)
    unit_counts = $unitCounts
    mission_counts = $missionCounts
    squadrons = @($squadrons)
    battalions = @($battalions)
    brigades = @($brigades)
    taskforces = @($taskForces)
    packages = @($packages)
    flights = @($flights)
}

$json = $result | ConvertTo-Json -Depth 32
if ($OutputPath) {
    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
else {
    $json
}
