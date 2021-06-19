// bot.ts
// Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import { D3DataSource, D3Datum } from './responsive'

export class BotCommand implements D3Datum {
    id: string
    name?: string

    constructor(data: any) {
        Object.assign(this, data)
        this.id = data.id.toString()
    }
}

export class BotData implements D3DataSource {
    private commands: BotCommand[] = []

    private initialFetch: Promise<void>

    constructor() {
        this.initialFetch = fetch('/web/api/v1/bot/commands').then(async (res) => {
            let data = await res.json()
            for (let d of data) this.commands.push(new BotCommand(d))
        })
    }

    async data(dtype: string): Promise<D3Datum[]> {
        await this.initialFetch
        switch (dtype) {
            case 'commands':
                return this.commands
            default:
                throw new Error(`No such data ${dtype} available`)
        }
    }
}
